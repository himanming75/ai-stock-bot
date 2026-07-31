from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

VERSION = "76.15"
SCHEMA = "v76.15.final_integrity_verification.1"
EXPECTED_SOURCE_NEXT = "V76_15_FINAL_INTEGRITY_VERIFICATION"
NEXT_PHASE = "V76_16_RELEASE_ARCHIVE_SEAL"


class IntegrityVerificationError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise IntegrityVerificationError(f"required JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise IntegrityVerificationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise IntegrityVerificationError(f"JSON root must be an object: {path}")
    return value


def validate_sha256(value: Any, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise IntegrityVerificationError(f"{name} must be a 64-character SHA256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise IntegrityVerificationError(f"{name} must be hexadecimal") from exc


def validate_commit(value: Any, name: str) -> None:
    if not isinstance(value, str) or len(value) != 40:
        raise IntegrityVerificationError(f"{name} must be a 40-character Git SHA")
    try:
        int(value, 16)
    except ValueError as exc:
        raise IntegrityVerificationError(f"{name} must be hexadecimal") from exc


def validate_config(config: dict[str, Any]) -> None:
    if config.get("verification_scope") != "FINAL_INTEGRITY_VERIFICATION":
        raise IntegrityVerificationError("verification_scope invalid")

    for key in (
        "offline_only",
        "require_git_tracked_clean",
        "require_head_matches_origin_main",
        "require_framework_commit_match",
        "require_manifest_self_hash_match",
        "require_anchor_chain_hash_match",
        "require_summary_match",
        "require_all_v76_14_gates_pass",
        "require_final_manifest_issued",
        "require_release_candidate_closed",
        "require_zero_trading_side_effects",
        "require_source_files_present",
    ):
        if config.get(key) is not True:
            raise IntegrityVerificationError(f"{key} must be true")

    for key in (
        "network_allowed",
        "broker_connection_allowed",
        "order_submission_allowed",
        "live_trading_allowed",
        "live_approval_allowed",
    ):
        if config.get(key) is not False:
            raise IntegrityVerificationError(f"{key} must be false")

    validate_commit(
        config.get("expected_framework_commit_sha"),
        "expected_framework_commit_sha",
    )
    validate_sha256(
        config.get("expected_final_manifest_sha256"),
        "expected_final_manifest_sha256",
    )
    validate_sha256(
        config.get("expected_immutable_anchor_chain_sha256"),
        "expected_immutable_anchor_chain_sha256",
    )

    if config.get("expected_v76_14_gate_count") != 69:
        raise IntegrityVerificationError("expected_v76_14_gate_count must be 69")

    source = config.get("v76_14_output_dir")
    if not isinstance(source, str) or not source:
        raise IntegrityVerificationError("v76_14_output_dir required")


def safe_relative(root: Path, relative_text: str) -> Path:
    relative = Path(relative_text)
    if relative.is_absolute() or ".." in relative.parts:
        raise IntegrityVerificationError(f"unsafe relative path: {relative_text}")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise IntegrityVerificationError(
            f"path outside repository: {relative_text}"
        ) from exc
    return resolved


def run_git(root: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise IntegrityVerificationError(
            f"git {' '.join(args)} failed: {completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def git_state(root: Path) -> dict[str, Any]:
    tracked = run_git(root, ["status", "--short", "--untracked-files=no"])
    full = run_git(root, ["status", "--short"])
    return {
        "head_sha": run_git(root, ["rev-parse", "HEAD"]),
        "origin_main_sha": run_git(root, ["rev-parse", "origin/main"]),
        "branch": run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"]),
        "tracked_status_short": tracked.splitlines() if tracked else [],
        "full_status_short": full.splitlines() if full else [],
    }


def add_gate(
    gates: list[dict[str, Any]],
    gate_id: str,
    passed: bool,
    **details: Any,
) -> None:
    gate = {"gate_id": gate_id, "status": "PASS" if passed else "FAIL"}
    gate.update(details)
    gates.append(gate)


def _source_manifest_material(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in manifest.items()
        if key not in {
            "final_manifest_sha256",
            "issued_at_utc",
            "duration_seconds",
        }
    }


def build_final_integrity_verification(
    root: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    root = root.resolve()
    validate_config(config)
    started = time.time()

    source_dir = safe_relative(root, config["v76_14_output_dir"])
    manifest_path = source_dir / "final_immutable_manifest_v76_14.json"
    summary_path = source_dir / "final_immutable_manifest_summary_v76_14.json"
    text_path = source_dir / "final_immutable_manifest_v76_14.txt"

    manifest = load_json(manifest_path)
    summary = load_json(summary_path)
    git = git_state(root)
    gates: list[dict[str, Any]] = []

    add_gate(
        gates, "GIT_HEAD_MATCHES_ORIGIN_MAIN",
        git["head_sha"] == git["origin_main_sha"],
        actual=git["head_sha"], expected=git["origin_main_sha"],
    )
    add_gate(
        gates, "GIT_HEAD_MATCHES_V76_14_FRAMEWORK_COMMIT",
        git["head_sha"] == config["expected_framework_commit_sha"],
        actual=git["head_sha"],
        expected=config["expected_framework_commit_sha"],
    )
    add_gate(
        gates, "GIT_BRANCH_MAIN", git["branch"] == "main",
        actual=git["branch"], expected="main",
    )
    add_gate(
        gates, "GIT_TRACKED_WORKING_TREE_CLEAN",
        git["tracked_status_short"] == [],
        actual=git["tracked_status_short"], expected=[],
    )

    add_gate(gates, "V76_14_MANIFEST_FILE_EXISTS", manifest_path.is_file())
    add_gate(gates, "V76_14_SUMMARY_FILE_EXISTS", summary_path.is_file())
    add_gate(gates, "V76_14_TEXT_FILE_EXISTS", text_path.is_file())

    stored_manifest_hash = manifest.get("final_manifest_sha256")
    calculated_manifest_hash = digest(_source_manifest_material(manifest))
    add_gate(
        gates, "V76_14_MANIFEST_SELF_HASH",
        stored_manifest_hash == calculated_manifest_hash,
        stored=stored_manifest_hash, calculated=calculated_manifest_hash,
    )
    add_gate(
        gates, "V76_14_MANIFEST_HASH_ANCHORED",
        stored_manifest_hash == config["expected_final_manifest_sha256"],
        actual=stored_manifest_hash,
        expected=config["expected_final_manifest_sha256"],
    )

    anchors = manifest.get("immutable_anchor_chain")
    calculated_anchor_hash = digest(anchors) if isinstance(anchors, dict) else None
    stored_anchor_hash = manifest.get("immutable_anchor_chain_sha256")
    add_gate(
        gates, "V76_14_ANCHOR_CHAIN_SELF_HASH",
        stored_anchor_hash == calculated_anchor_hash,
        stored=stored_anchor_hash, calculated=calculated_anchor_hash,
    )
    add_gate(
        gates, "V76_14_ANCHOR_CHAIN_HASH_ANCHORED",
        stored_anchor_hash == config["expected_immutable_anchor_chain_sha256"],
        actual=stored_anchor_hash,
        expected=config["expected_immutable_anchor_chain_sha256"],
    )

    result_data = manifest.get("manifest_result", {})
    gate_count = result_data.get("gate_count")
    passed_count = result_data.get("passed_gate_count")
    failed_count = result_data.get("failed_gate_count")
    failed_ids = result_data.get("failed_gate_ids")
    source_gates = result_data.get("gates")

    add_gate(
        gates, "V76_14_STATUS_PASS", manifest.get("status") == "PASS",
        actual=manifest.get("status"), expected="PASS",
    )
    add_gate(
        gates, "V76_14_DECISION_ISSUED",
        manifest.get("decision") == "final_immutable_manifest_issued",
        actual=manifest.get("decision"),
        expected="final_immutable_manifest_issued",
    )
    add_gate(
        gates, "V76_14_GATE_COUNT",
        gate_count == config["expected_v76_14_gate_count"],
        actual=gate_count, expected=config["expected_v76_14_gate_count"],
    )
    add_gate(
        gates, "V76_14_ALL_GATES_PASSED",
        isinstance(source_gates, list)
        and len(source_gates) == config["expected_v76_14_gate_count"]
        and all(
            isinstance(gate, dict) and gate.get("status") == "PASS"
            for gate in source_gates
        ),
    )
    add_gate(
        gates, "V76_14_PASSED_GATE_COUNT",
        passed_count == config["expected_v76_14_gate_count"],
        actual=passed_count, expected=config["expected_v76_14_gate_count"],
    )
    add_gate(
        gates, "V76_14_FAILED_GATE_COUNT_ZERO",
        failed_count == 0, actual=failed_count, expected=0,
    )
    add_gate(
        gates, "V76_14_FAILED_GATE_IDS_EMPTY",
        failed_ids == [], actual=failed_ids, expected=[],
    )
    add_gate(
        gates, "V76_14_FINAL_MANIFEST_ISSUED",
        manifest.get("final_manifest_issued") is True,
    )
    add_gate(
        gates, "V76_14_RELEASE_CANDIDATE_CLOSED",
        manifest.get("release_candidate_closed") is True,
    )
    add_gate(
        gates, "V76_14_NEXT_PHASE",
        manifest.get("next_phase") == EXPECTED_SOURCE_NEXT,
        actual=manifest.get("next_phase"), expected=EXPECTED_SOURCE_NEXT,
    )

    summary_expectations = {
        "status": manifest.get("status"),
        "decision": manifest.get("decision"),
        "framework_commit_sha": manifest.get("repository", {}).get(
            "framework_commit_sha"
        ),
        "final_manifest_sha256": stored_manifest_hash,
        "immutable_anchor_chain_sha256": stored_anchor_hash,
        "gate_count": gate_count,
        "passed_gate_count": passed_count,
        "failed_gate_count": failed_count,
        "failed_gate_ids": failed_ids,
        "final_manifest_issued": manifest.get("final_manifest_issued"),
        "release_candidate_closed": manifest.get("release_candidate_closed"),
        "network_allowed": manifest.get("network_allowed"),
        "orders_submitted": manifest.get("orders_submitted"),
        "approved_for_live": manifest.get("approved_for_live"),
        "live_trading_authorized": manifest.get("live_trading_authorized"),
        "next_phase": manifest.get("next_phase"),
    }
    for key, expected in summary_expectations.items():
        add_gate(
            gates, f"V76_14_SUMMARY_{key.upper()}",
            summary.get(key) == expected,
            actual=summary.get(key), expected=expected,
        )

    add_gate(
        gates, "OFFLINE_ONLY_POLICY", config.get("offline_only") is True,
    )
    add_gate(
        gates, "NETWORK_DISABLED",
        manifest.get("network_allowed") is False,
    )
    add_gate(
        gates, "BROKER_NOT_CONNECTED",
        manifest.get("broker_connected") is False,
    )
    add_gate(
        gates, "ZERO_ORDERS_SUBMITTED",
        manifest.get("orders_submitted") == 0,
        actual=manifest.get("orders_submitted"), expected=0,
    )
    add_gate(
        gates, "NOT_APPROVED_FOR_LIVE",
        manifest.get("approved_for_live") is False,
    )
    add_gate(
        gates, "LIVE_TRADING_NOT_AUTHORIZED",
        manifest.get("live_trading_authorized") is False,
    )

    artifact_hashes = {
        "final_immutable_manifest_v76_14.json": file_sha256(manifest_path),
        "final_immutable_manifest_summary_v76_14.json": file_sha256(summary_path),
        "final_immutable_manifest_v76_14.txt": file_sha256(text_path),
    }
    artifact_set_sha256 = digest(artifact_hashes)

    failed = [gate["gate_id"] for gate in gates if gate["status"] != "PASS"]
    passed = len(gates) - len(failed)
    status = "PASS" if not failed else "FAIL"

    result: dict[str, Any] = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "verification_type": "FINAL_IMMUTABLE_MANIFEST_INTEGRITY_VERIFICATION",
        "issued_at_utc": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(time.time() - started, 6),
        "status": status,
        "decision": (
            "final_immutable_manifest_integrity_verified"
            if status == "PASS"
            else "final_immutable_manifest_integrity_verification_failed"
        ),
        "repository": {
            "framework_commit_sha": git["head_sha"],
            "origin_main_sha": git["origin_main_sha"],
            "branch": git["branch"],
            "tracked_working_tree_clean": git["tracked_status_short"] == [],
        },
        "source": {
            "version": "76.14",
            "final_manifest_sha256": stored_manifest_hash,
            "immutable_anchor_chain_sha256": stored_anchor_hash,
            "artifact_file_sha256": artifact_hashes,
            "artifact_set_sha256": artifact_set_sha256,
        },
        "verification_result": {
            "gate_count": len(gates),
            "passed_gate_count": passed,
            "failed_gate_count": len(failed),
            "failed_gate_ids": failed,
            "gates": gates,
        },
        "final_manifest_independently_verified": status == "PASS",
        "release_candidate_closed": status == "PASS",
        "network_allowed": False,
        "broker_connected": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "next_phase": NEXT_PHASE if status == "PASS" else (
            "REPAIR_V76_15_FINAL_INTEGRITY_VERIFICATION"
        ),
    }

    immutable_material = {
        key: value
        for key, value in result.items()
        if key not in {"issued_at_utc", "duration_seconds"}
    }
    result["verification_sha256"] = digest(immutable_material)
    return result


def summary_from(result: dict[str, Any]) -> dict[str, Any]:
    verification = result["verification_result"]
    source = result["source"]
    return {
        "status": result["status"],
        "decision": result["decision"],
        "framework_commit_sha": result["repository"]["framework_commit_sha"],
        "verification_sha256": result["verification_sha256"],
        "final_manifest_sha256": source["final_manifest_sha256"],
        "immutable_anchor_chain_sha256": source[
            "immutable_anchor_chain_sha256"
        ],
        "artifact_set_sha256": source["artifact_set_sha256"],
        "gate_count": verification["gate_count"],
        "passed_gate_count": verification["passed_gate_count"],
        "failed_gate_count": verification["failed_gate_count"],
        "failed_gate_ids": verification["failed_gate_ids"],
        "final_manifest_independently_verified": result[
            "final_manifest_independently_verified"
        ],
        "release_candidate_closed": result["release_candidate_closed"],
        "network_allowed": result["network_allowed"],
        "orders_submitted": result["orders_submitted"],
        "approved_for_live": result["approved_for_live"],
        "live_trading_authorized": result["live_trading_authorized"],
        "next_phase": result["next_phase"],
    }


def render_text(result: dict[str, Any]) -> str:
    verification = result["verification_result"]
    source = result["source"]
    lines = [
        "V76.15 FINAL INTEGRITY VERIFICATION",
        f"status: {result['status']}",
        f"decision: {result['decision']}",
        f"framework_commit_sha: {result['repository']['framework_commit_sha']}",
        f"final_manifest_sha256: {source['final_manifest_sha256']}",
        "immutable_anchor_chain_sha256: "
        f"{source['immutable_anchor_chain_sha256']}",
        f"artifact_set_sha256: {source['artifact_set_sha256']}",
        f"verification_sha256: {result['verification_sha256']}",
        f"gate_count: {verification['gate_count']}",
        f"passed_gate_count: {verification['passed_gate_count']}",
        f"failed_gate_count: {verification['failed_gate_count']}",
        f"failed_gate_ids: {verification['failed_gate_ids']}",
        "final_manifest_independently_verified: "
        f"{result['final_manifest_independently_verified']}",
        f"release_candidate_closed: {result['release_candidate_closed']}",
        f"network_allowed: {result['network_allowed']}",
        f"orders_submitted: {result['orders_submitted']}",
        f"approved_for_live: {result['approved_for_live']}",
        f"live_trading_authorized: {result['live_trading_authorized']}",
        f"next_phase: {result['next_phase']}",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(result: dict[str, Any], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "final_integrity_verification_v76_15.json"
    summary_path = output_dir / (
        "final_integrity_verification_summary_v76_15.json"
    )
    text_path = output_dir / "final_integrity_verification_v76_15.txt"

    manifest_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    summary_path.write_text(
        json.dumps(
            summary_from(result), indent=2, sort_keys=True, ensure_ascii=False
        ) + "\n",
        encoding="utf-8",
    )
    text_path.write_text(render_text(result), encoding="utf-8")
    return [manifest_path, summary_path, text_path]


def cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    root = Path(args.repository_root)
    config = load_json(Path(args.config))
    result = build_final_integrity_verification(root, config)
    outputs = write_outputs(result, Path(args.output_dir))
    vr = result["verification_result"]
    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "gate_count": vr["gate_count"],
        "passed_gate_count": vr["passed_gate_count"],
        "failed_gate_count": vr["failed_gate_count"],
        "failed_gate_ids": vr["failed_gate_ids"],
        "final_manifest_independently_verified": result[
            "final_manifest_independently_verified"
        ],
        "release_candidate_closed": result["release_candidate_closed"],
        "verification_sha256": result["verification_sha256"],
        "artifact_set_sha256": result["source"]["artifact_set_sha256"],
        "final_manifest_sha256": result["source"]["final_manifest_sha256"],
        "immutable_anchor_chain_sha256": result["source"][
            "immutable_anchor_chain_sha256"
        ],
        "network_allowed": result["network_allowed"],
        "orders_submitted": result["orders_submitted"],
        "approved_for_live": result["approved_for_live"],
        "live_trading_authorized": result["live_trading_authorized"],
        "next_phase": result["next_phase"],
        "outputs": [str(path) for path in outputs],
    }, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(cli())
