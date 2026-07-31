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

VERSION = "76.14"
SCHEMA = "v76.14.final_immutable_manifest.1"


class ManifestError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestError(f"required JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ManifestError(f"JSON root must be an object: {path}")
    return value


def validate_sha256(value: Any, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ManifestError(f"{name} must be a 64-character SHA256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ManifestError(f"{name} must be hexadecimal") from exc


def validate_commit(value: Any, name: str) -> None:
    if not isinstance(value, str) or len(value) != 40:
        raise ManifestError(f"{name} must be a 40-character Git SHA")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ManifestError(f"{name} must be hexadecimal") from exc


def validate_config(config: dict[str, Any]) -> None:
    if config.get("manifest_scope") != "FINAL_IMMUTABLE_MANIFEST":
        raise ManifestError("manifest_scope invalid")

    required_true = (
        "offline_only",
        "require_git_tracked_clean",
        "require_head_matches_origin_main",
        "require_framework_commit_match",
        "require_v76_13_self_hash_match",
        "require_v76_13_hash_anchor",
        "require_v76_13_summary_match",
        "require_all_v76_13_gates_pass",
        "require_release_candidate_closed",
        "require_complete_anchor_chain",
        "require_zero_trading_side_effects",
    )
    required_false = (
        "network_allowed",
        "broker_connection_allowed",
        "order_submission_allowed",
        "live_trading_allowed",
        "live_approval_allowed",
    )
    for key in required_true:
        if config.get(key) is not True:
            raise ManifestError(f"{key} must be true")
    for key in required_false:
        if config.get(key) is not False:
            raise ManifestError(f"{key} must be false")

    validate_commit(
        config.get("expected_framework_commit_sha"),
        "expected_framework_commit_sha",
    )
    validate_sha256(
        config.get("expected_v76_13_verification_sha256"),
        "expected_v76_13_verification_sha256",
    )
    if config.get("expected_v76_13_gate_count") != 45:
        raise ManifestError("expected_v76_13_gate_count must be 45")

    source = config.get("v76_13_output_dir")
    if not isinstance(source, str) or not source:
        raise ManifestError("v76_13_output_dir required")

    anchors = config.get("immutable_anchor_chain")
    if not isinstance(anchors, dict) or set(anchors) != {
        "v76_6", "v76_7", "v76_8", "v76_9",
        "v76_10", "v76_11", "v76_12", "v76_13",
    }:
        raise ManifestError("immutable_anchor_chain must contain v76_6 through v76_13")

    for version, values in anchors.items():
        if not isinstance(values, dict):
            raise ManifestError(f"{version} anchor must be an object")
        for key, value in values.items():
            if key.endswith("commit_sha"):
                validate_commit(value, f"{version}.{key}")
            elif key.endswith("sha256"):
                validate_sha256(value, f"{version}.{key}")


def safe_relative(root: Path, relative_text: str) -> Path:
    relative = Path(relative_text)
    if relative.is_absolute() or ".." in relative.parts:
        raise ManifestError(f"unsafe relative path: {relative_text}")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ManifestError(f"path outside repository: {relative_text}") from exc
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
        raise ManifestError(
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


def build_final_immutable_manifest(
    root: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    root = root.resolve()
    validate_config(config)
    started = time.time()

    source_dir = safe_relative(root, config["v76_13_output_dir"])
    verification_path = source_dir / (
        "release_candidate_closure_verification_v76_13.json"
    )
    summary_path = source_dir / (
        "release_candidate_closure_verification_summary_v76_13.json"
    )
    text_path = source_dir / (
        "release_candidate_closure_verification_v76_13.txt"
    )

    verification = load_json(verification_path)
    summary = load_json(summary_path)
    git = git_state(root)
    gates: list[dict[str, Any]] = []

    add_gate(
        gates,
        "GIT_HEAD_MATCHES_ORIGIN_MAIN",
        git["head_sha"] == git["origin_main_sha"],
        actual=git["head_sha"],
        expected=git["origin_main_sha"],
    )
    add_gate(
        gates,
        "GIT_HEAD_MATCHES_V76_13_FRAMEWORK_COMMIT",
        git["head_sha"] == config["expected_framework_commit_sha"],
        actual=git["head_sha"],
        expected=config["expected_framework_commit_sha"],
    )
    add_gate(
        gates,
        "GIT_BRANCH_MAIN",
        git["branch"] == "main",
        actual=git["branch"],
        expected="main",
    )
    add_gate(
        gates,
        "GIT_TRACKED_WORKING_TREE_CLEAN",
        git["tracked_status_short"] == [],
        actual=git["tracked_status_short"],
        expected=[],
    )
    add_gate(gates, "V76_13_TEXT_VERIFICATION_EXISTS", text_path.is_file())

    stored_hash = verification.get("verification_sha256")
    calculated_hash = digest(
        {
            key: value
            for key, value in verification.items()
            if key != "verification_sha256"
        }
    )
    add_gate(
        gates,
        "V76_13_VERIFICATION_SELF_HASH",
        stored_hash == calculated_hash,
        stored=stored_hash,
        calculated=calculated_hash,
    )
    add_gate(
        gates,
        "V76_13_VERIFICATION_HASH_ANCHORED",
        stored_hash == config["expected_v76_13_verification_sha256"],
        actual=stored_hash,
        expected=config["expected_v76_13_verification_sha256"],
    )

    result_data = verification.get("verification_result", {})
    gate_count = result_data.get("gate_count")
    passed_count = result_data.get("passed_gate_count")
    failed_count = result_data.get("failed_gate_count")
    failed_ids = result_data.get("failed_gate_ids")
    source_gates = result_data.get("gates")

    checks = {
        "V76_13_STATUS_PASS": verification.get("status") == "PASS",
        "V76_13_DECISION_VERIFIED":
            verification.get("decision")
            == "release_candidate_closure_certificate_independently_verified",
        "V76_13_CLOSURE_VERIFIED_TRUE":
            verification.get(
                "closure_certificate_independently_verified"
            ) is True,
        "V76_13_RELEASE_CANDIDATE_CLOSED_TRUE":
            verification.get("release_candidate_closed") is True,
        "V76_13_GATE_COUNT":
            gate_count == config["expected_v76_13_gate_count"],
        "V76_13_PASSED_GATE_COUNT":
            passed_count == config["expected_v76_13_gate_count"],
        "V76_13_FAILED_GATE_COUNT_ZERO": failed_count == 0,
        "V76_13_FAILED_GATE_IDS_EMPTY": failed_ids == [],
        "V76_13_GATE_LIST_PRESENT":
            isinstance(source_gates, list)
            and len(source_gates) == config["expected_v76_13_gate_count"],
        "V76_13_ALL_SOURCE_GATES_PASS":
            isinstance(source_gates, list)
            and all(
                isinstance(gate, dict) and gate.get("status") == "PASS"
                for gate in source_gates
            ),
        "V76_13_NEXT_PHASE":
            verification.get("next_phase")
            == "V76_14_FINAL_IMMUTABLE_MANIFEST",
    }
    for gate_id, passed in checks.items():
        add_gate(gates, gate_id, passed)

    summary_checks = {
        "V76_13_SUMMARY_STATUS":
            summary.get("status") == verification.get("status"),
        "V76_13_SUMMARY_DECISION":
            summary.get("decision") == verification.get("decision"),
        "V76_13_SUMMARY_FRAMEWORK_COMMIT":
            summary.get("framework_commit_sha")
            == verification.get("repository", {}).get("framework_commit_sha"),
        "V76_13_SUMMARY_VERIFICATION_HASH":
            summary.get("verification_sha256") == stored_hash,
        "V76_13_SUMMARY_GATE_COUNT":
            summary.get("gate_count") == gate_count,
        "V76_13_SUMMARY_PASSED_GATE_COUNT":
            summary.get("passed_gate_count") == passed_count,
        "V76_13_SUMMARY_FAILED_GATE_COUNT":
            summary.get("failed_gate_count") == failed_count,
        "V76_13_SUMMARY_FAILED_GATE_IDS":
            summary.get("failed_gate_ids") == failed_ids,
        "V76_13_SUMMARY_CLOSURE_VERIFIED":
            summary.get(
                "closure_certificate_independently_verified"
            ) is True,
        "V76_13_SUMMARY_RELEASE_CANDIDATE_CLOSED":
            summary.get("release_candidate_closed") is True,
        "V76_13_SUMMARY_NEXT_PHASE":
            summary.get("next_phase")
            == "V76_14_FINAL_IMMUTABLE_MANIFEST",
    }
    for gate_id, passed in summary_checks.items():
        add_gate(gates, gate_id, passed)

    anchors = config["immutable_anchor_chain"]
    expected_versions = [
        "v76_6", "v76_7", "v76_8", "v76_9",
        "v76_10", "v76_11", "v76_12", "v76_13",
    ]
    actual_versions = list(anchors.keys())
    add_gate(
        gates,
        "IMMUTABLE_ANCHOR_VERSION_SET",
        len(actual_versions) == len(expected_versions)
        and set(actual_versions) == set(expected_versions),
        actual=sorted(actual_versions),
        expected=sorted(expected_versions),
    )

    for version in expected_versions:
        values = anchors[version]
        add_gate(
            gates,
            f"{version.upper()}_ANCHOR_OBJECT_NONEMPTY",
            isinstance(values, dict) and bool(values),
        )
        for key, value in values.items():
            if key.endswith("commit_sha"):
                valid = isinstance(value, str) and len(value) == 40
            elif key.endswith("sha256"):
                valid = isinstance(value, str) and len(value) == 64
            else:
                valid = False
            add_gate(
                gates,
                f"{version.upper()}_{key.upper()}_FORMAT",
                valid,
            )

    add_gate(
        gates,
        "V76_13_ANCHOR_COMMIT_MATCHES_FRAMEWORK",
        anchors["v76_13"]["commit_sha"]
        == config["expected_framework_commit_sha"],
        actual=anchors["v76_13"]["commit_sha"],
        expected=config["expected_framework_commit_sha"],
    )
    add_gate(
        gates,
        "V76_13_ANCHOR_HASH_MATCHES_SOURCE",
        anchors["v76_13"]["verification_sha256"] == stored_hash,
        actual=anchors["v76_13"]["verification_sha256"],
        expected=stored_hash,
    )

    safety_checks = {
        "V76_13_NETWORK_FALSE":
            verification.get("network_allowed") is False,
        "V76_13_BROKER_CONNECTED_FALSE":
            verification.get("broker_connected") is False,
        "V76_13_ORDERS_ZERO":
            verification.get("orders_submitted") == 0,
        "V76_13_APPROVED_FOR_LIVE_FALSE":
            verification.get("approved_for_live") is False,
        "V76_13_LIVE_TRADING_AUTHORIZED_FALSE":
            verification.get("live_trading_authorized") is False,
        "V76_13_SUMMARY_NETWORK_FALSE":
            summary.get("network_allowed") is False,
        "V76_13_SUMMARY_ORDERS_ZERO":
            summary.get("orders_submitted") == 0,
        "V76_13_SUMMARY_APPROVED_FOR_LIVE_FALSE":
            summary.get("approved_for_live") is False,
        "V76_13_SUMMARY_LIVE_TRADING_AUTHORIZED_FALSE":
            summary.get("live_trading_authorized") is False,
    }
    for gate_id, passed in safety_checks.items():
        add_gate(gates, gate_id, passed)

    anchor_chain_sha256 = digest(anchors)
    failed = [g["gate_id"] for g in gates if g["status"] != "PASS"]
    status = "PASS" if not failed else "FAIL"

    manifest = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "manifest_type": "FINAL_IMMUTABLE_MANIFEST",
        "status": status,
        "decision": (
            "final_immutable_manifest_issued"
            if status == "PASS"
            else "final_immutable_manifest_failed"
        ),
        "issued_at_utc":
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "repository": {
            "branch": git["branch"],
            "framework_commit_sha": git["head_sha"],
            "origin_main_sha": git["origin_main_sha"],
            "tracked_working_tree_clean":
                git["tracked_status_short"] == [],
        },
        "source_v76_13_verification": {
            "verification_sha256": stored_hash,
            "status": verification.get("status"),
            "decision": verification.get("decision"),
            "closure_certificate_independently_verified":
                verification.get(
                    "closure_certificate_independently_verified"
                ),
            "release_candidate_closed":
                verification.get("release_candidate_closed"),
            "v76_13_gate_count": gate_count,
            "v76_13_passed_gate_count": passed_count,
            "v76_13_failed_gate_count": failed_count,
        },
        "immutable_anchor_chain": anchors,
        "immutable_anchor_chain_sha256": anchor_chain_sha256,
        "manifest_result": {
            "gate_count": len(gates),
            "passed_gate_count": len(gates) - len(failed),
            "failed_gate_count": len(failed),
            "failed_gate_ids": failed,
            "gates": gates,
        },
        "final_manifest_issued": status == "PASS",
        "release_candidate_closed": status == "PASS",
        "network_allowed": False,
        "broker_connected": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "duration_seconds": round(time.time() - started, 6),
        "next_phase": (
            "V76_15_FINAL_INTEGRITY_VERIFICATION"
            if status == "PASS"
            else "REPAIR_V76_14_FINAL_IMMUTABLE_MANIFEST"
        ),
    }
    immutable_material = {
        key: value
        for key, value in manifest.items()
        if key not in {"issued_at_utc", "duration_seconds"}
    }
    manifest["final_manifest_sha256"] = digest(immutable_material)
    return manifest


def write_outputs(result: dict[str, Any], output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "final_immutable_manifest_v76_14.json"
    summary_path = output_dir / "final_immutable_manifest_summary_v76_14.json"
    text_path = output_dir / "final_immutable_manifest_v76_14.txt"

    manifest_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    manifest_result = result["manifest_result"]
    summary = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "status": result["status"],
        "decision": result["decision"],
        "framework_commit_sha":
            result["repository"]["framework_commit_sha"],
        "immutable_anchor_chain_sha256":
            result["immutable_anchor_chain_sha256"],
        "final_manifest_sha256": result["final_manifest_sha256"],
        "gate_count": manifest_result["gate_count"],
        "passed_gate_count": manifest_result["passed_gate_count"],
        "failed_gate_count": manifest_result["failed_gate_count"],
        "failed_gate_ids": manifest_result["failed_gate_ids"],
        "final_manifest_issued": result["final_manifest_issued"],
        "release_candidate_closed": result["release_candidate_closed"],
        "network_allowed": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "next_phase": result["next_phase"],
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "V76.14 FINAL IMMUTABLE MANIFEST",
        "=" * 39,
        f"Status: {result['status']}",
        f"Decision: {result['decision']}",
        f"Final manifest issued: {result['final_manifest_issued']}",
        f"Release candidate closed: {result['release_candidate_closed']}",
        f"Gate count: {manifest_result['gate_count']}",
        f"Passed gates: {manifest_result['passed_gate_count']}",
        f"Failed gates: {manifest_result['failed_gate_count']}",
        "Immutable anchor chain SHA256: "
        f"{result['immutable_anchor_chain_sha256']}",
        f"Final manifest SHA256: {result['final_manifest_sha256']}",
        f"Network allowed: {result['network_allowed']}",
        f"Orders submitted: {result['orders_submitted']}",
        f"Approved for live: {result['approved_for_live']}",
        f"Live trading authorized: {result['live_trading_authorized']}",
        f"Next phase: {result['next_phase']}",
    ]
    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return [str(manifest_path), str(summary_path), str(text_path)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    root = Path(args.repository_root)
    config = load_json(Path(args.config))
    result = build_final_immutable_manifest(root, config)
    outputs = write_outputs(result, Path(args.output_dir))
    manifest_result = result["manifest_result"]

    printed = {
        "approved_for_live": result["approved_for_live"],
        "decision": result["decision"],
        "failed_gate_count": manifest_result["failed_gate_count"],
        "failed_gate_ids": manifest_result["failed_gate_ids"],
        "final_manifest_issued": result["final_manifest_issued"],
        "final_manifest_sha256": result["final_manifest_sha256"],
        "gate_count": manifest_result["gate_count"],
        "immutable_anchor_chain_sha256":
            result["immutable_anchor_chain_sha256"],
        "live_trading_authorized":
            result["live_trading_authorized"],
        "network_allowed": result["network_allowed"],
        "next_phase": result["next_phase"],
        "orders_submitted": result["orders_submitted"],
        "outputs": outputs,
        "passed_gate_count": manifest_result["passed_gate_count"],
        "release_candidate_closed": result["release_candidate_closed"],
        "status": result["status"],
    }
    print(json.dumps(printed, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
