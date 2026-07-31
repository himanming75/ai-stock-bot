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

VERSION = "76.18"
SCHEMA = "v76.18.release_archive_closure_certificate.1"
NEXT_PHASE = "V76_19_RELEASE_ARCHIVE_CLOSURE_VERIFICATION"


class ClosureCertificateError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ClosureCertificateError(f"required JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ClosureCertificateError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ClosureCertificateError(f"JSON root must be object: {path}")
    return value


def validate_hex(value: Any, length: int, name: str) -> None:
    if not isinstance(value, str) or len(value) != length:
        raise ClosureCertificateError(f"{name} must be {length} hexadecimal characters")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ClosureCertificateError(f"{name} must be hexadecimal") from exc


def validate_config(config: dict[str, Any]) -> None:
    if config.get("certificate_scope") != "RELEASE_ARCHIVE_CLOSURE_CERTIFICATE":
        raise ClosureCertificateError("certificate_scope invalid")
    for key in (
        "offline_only",
        "deterministic_certificate_required",
        "require_git_tracked_clean",
        "require_head_matches_origin_main",
        "require_framework_commit_match",
        "require_v76_16_seal",
        "require_v76_17_verification",
        "require_zero_failed_gates",
        "require_anchor_chain_consistency",
        "require_zero_trading_side_effects",
    ):
        if config.get(key) is not True:
            raise ClosureCertificateError(f"{key} must be true")
    for key in (
        "network_allowed",
        "broker_connection_allowed",
        "order_submission_allowed",
        "live_trading_allowed",
        "live_approval_allowed",
    ):
        if config.get(key) is not False:
            raise ClosureCertificateError(f"{key} must be false")

    validate_hex(config.get("expected_framework_commit_sha"), 40,
                 "expected_framework_commit_sha")
    for key in (
        "expected_v76_17_verification_sha256",
        "expected_v76_16_seal_certificate_sha256",
        "expected_v76_16_archive_sha256",
        "expected_v76_16_archive_manifest_sha256",
        "expected_v76_16_evidence_set_sha256",
    ):
        validate_hex(config.get(key), 64, key)


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
        raise ClosureCertificateError(
            f"git {' '.join(args)} failed: {completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def git_state(root: Path) -> dict[str, Any]:
    tracked = run_git(root, ["status", "--short", "--untracked-files=no"])
    return {
        "head_sha": run_git(root, ["rev-parse", "HEAD"]),
        "origin_main_sha": run_git(root, ["rev-parse", "origin/main"]),
        "branch": run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"]),
        "tracked_status_short": tracked.splitlines() if tracked else [],
    }


def add_gate(gates: list[dict[str, Any]], gate_id: str,
             passed: bool, **details: Any) -> None:
    gate = {"gate_id": gate_id, "status": "PASS" if passed else "FAIL"}
    gate.update(details)
    gates.append(gate)


def create_closure_certificate(
    root: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    root = root.resolve()
    validate_config(config)
    started = time.time()
    git = git_state(root)
    gates: list[dict[str, Any]] = []

    add_gate(gates, "GIT_HEAD_MATCHES_ORIGIN_MAIN",
             git["head_sha"] == git["origin_main_sha"])
    add_gate(gates, "GIT_HEAD_MATCHES_FRAMEWORK_COMMIT",
             git["head_sha"] == config["expected_framework_commit_sha"])
    add_gate(gates, "GIT_BRANCH_MAIN", git["branch"] == "main")
    add_gate(gates, "GIT_TRACKED_WORKING_TREE_CLEAN",
             git["tracked_status_short"] == [])

    v16_path = root / "release/v76_16/output/release_archive_seal_v76_16.json"
    v17_path = root / "release/v76_17/output/release_archive_seal_verification_v76_17.json"
    add_gate(gates, "V76_16_RESULT_EXISTS", v16_path.is_file())
    add_gate(gates, "V76_17_RESULT_EXISTS", v17_path.is_file())

    v16 = load_json(v16_path)
    v17 = load_json(v17_path)

    v16_cert = v16.get("seal_certificate_sha256")
    v16_calc = digest({
        key: value for key, value in v16.items()
        if key not in {"seal_certificate_sha256", "issued_at_utc", "duration_seconds"}
    })
    add_gate(gates, "V76_16_CERTIFICATE_SELF_HASH", v16_cert == v16_calc)
    add_gate(gates, "V76_16_CERTIFICATE_ANCHORED",
             v16_cert == config["expected_v76_16_seal_certificate_sha256"])
    add_gate(gates, "V76_16_STATUS_PASS", v16.get("status") == "PASS")
    add_gate(gates, "V76_16_DECISION_SEALED",
             v16.get("decision") == "release_archive_sealed")
    add_gate(gates, "V76_16_RELEASE_ARCHIVE_SEALED",
             v16.get("release_archive_sealed") is True)
    add_gate(gates, "V76_16_RELEASE_CANDIDATE_CLOSED",
             v16.get("release_candidate_closed") is True)

    v16_archive = v16.get("archive", {})
    add_gate(gates, "V76_16_ARCHIVE_HASH_ANCHORED",
             v16_archive.get("sha256") ==
             config["expected_v76_16_archive_sha256"])
    add_gate(gates, "V76_16_MANIFEST_HASH_ANCHORED",
             v16_archive.get("archive_manifest_sha256") ==
             config["expected_v76_16_archive_manifest_sha256"])
    add_gate(gates, "V76_16_EVIDENCE_HASH_ANCHORED",
             v16_archive.get("evidence_set_sha256") ==
             config["expected_v76_16_evidence_set_sha256"])

    v16_gates = v16.get("seal_result", {})
    add_gate(gates, "V76_16_ZERO_FAILED_GATES",
             v16_gates.get("failed_gate_count") == 0)
    add_gate(gates, "V76_16_FAILED_GATE_IDS_EMPTY",
             v16_gates.get("failed_gate_ids") == [])

    v17_verify = v17.get("verification_sha256")
    v17_calc = digest({
        key: value for key, value in v17.items()
        if key not in {"verification_sha256", "issued_at_utc", "duration_seconds"}
    })
    add_gate(gates, "V76_17_VERIFICATION_SELF_HASH",
             v17_verify == v17_calc)
    add_gate(gates, "V76_17_VERIFICATION_ANCHORED",
             v17_verify == config["expected_v76_17_verification_sha256"])
    add_gate(gates, "V76_17_STATUS_PASS", v17.get("status") == "PASS")
    add_gate(gates, "V76_17_DECISION_VERIFIED",
             v17.get("decision") ==
             "release_archive_seal_independently_verified")
    add_gate(gates, "V76_17_INDEPENDENTLY_VERIFIED",
             v17.get("release_archive_independently_verified") is True)
    add_gate(gates, "V76_17_ARCHIVE_SEALED",
             v17.get("release_archive_sealed") is True)
    add_gate(gates, "V76_17_RELEASE_CANDIDATE_CLOSED",
             v17.get("release_candidate_closed") is True)

    v17_gates = v17.get("verification_result", {})
    add_gate(gates, "V76_17_ZERO_FAILED_GATES",
             v17_gates.get("failed_gate_count") == 0)
    add_gate(gates, "V76_17_FAILED_GATE_IDS_EMPTY",
             v17_gates.get("failed_gate_ids") == [])

    anchors = v17.get("verified_anchors", {})
    add_gate(gates, "V76_17_V16_CERT_MATCH",
             anchors.get("v76_16_seal_certificate_sha256") ==
             config["expected_v76_16_seal_certificate_sha256"])
    add_gate(gates, "V76_17_V16_ARCHIVE_MATCH",
             anchors.get("v76_16_archive_sha256") ==
             config["expected_v76_16_archive_sha256"])
    add_gate(gates, "V76_17_V16_MANIFEST_MATCH",
             anchors.get("v76_16_archive_manifest_sha256") ==
             config["expected_v76_16_archive_manifest_sha256"])
    add_gate(gates, "V76_17_V16_EVIDENCE_MATCH",
             anchors.get("v76_16_evidence_set_sha256") ==
             config["expected_v76_16_evidence_set_sha256"])

    safety_checks = {
        "V76_16_NETWORK_DISABLED": v16.get("network_allowed") is False,
        "V76_16_BROKER_NOT_CONNECTED": v16.get("broker_connected") is False,
        "V76_16_ZERO_ORDERS": v16.get("orders_submitted") == 0,
        "V76_16_NOT_APPROVED_FOR_LIVE": v16.get("approved_for_live") is False,
        "V76_16_LIVE_TRADING_NOT_AUTHORIZED":
            v16.get("live_trading_authorized") is False,
        "V76_17_NETWORK_DISABLED": v17.get("network_allowed") is False,
        "V76_17_BROKER_NOT_CONNECTED": v17.get("broker_connected") is False,
        "V76_17_ZERO_ORDERS": v17.get("orders_submitted") == 0,
        "V76_17_NOT_APPROVED_FOR_LIVE": v17.get("approved_for_live") is False,
        "V76_17_LIVE_TRADING_NOT_AUTHORIZED":
            v17.get("live_trading_authorized") is False,
    }
    for gate_id, passed in safety_checks.items():
        add_gate(gates, gate_id, passed)

    failed = [gate["gate_id"] for gate in gates if gate["status"] != "PASS"]
    status = "PASS" if not failed else "FAIL"

    closure_chain = {
        "framework_commit_sha": config["expected_framework_commit_sha"],
        "v76_16_seal_certificate_sha256":
            config["expected_v76_16_seal_certificate_sha256"],
        "v76_16_archive_sha256":
            config["expected_v76_16_archive_sha256"],
        "v76_16_archive_manifest_sha256":
            config["expected_v76_16_archive_manifest_sha256"],
        "v76_16_evidence_set_sha256":
            config["expected_v76_16_evidence_set_sha256"],
        "v76_17_verification_sha256":
            config["expected_v76_17_verification_sha256"],
    }
    closure_chain_sha256 = digest(closure_chain)

    result = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "certificate_type": "RELEASE_ARCHIVE_CLOSURE_CERTIFICATE",
        "issued_at_utc": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(time.time() - started, 6),
        "status": status,
        "decision": "release_archive_closure_certified"
                    if status == "PASS"
                    else "release_archive_closure_certificate_failed",
        "repository": {
            "framework_commit_sha": git["head_sha"],
            "origin_main_sha": git["origin_main_sha"],
            "branch": git["branch"],
            "tracked_working_tree_clean": git["tracked_status_short"] == [],
        },
        "closure_chain": closure_chain,
        "closure_chain_sha256": closure_chain_sha256,
        "certificate_result": {
            "gate_count": len(gates),
            "passed_gate_count": len(gates) - len(failed),
            "failed_gate_count": len(failed),
            "failed_gate_ids": failed,
            "gates": gates,
        },
        "release_archive_closure_certified": status == "PASS",
        "release_archive_independently_verified": status == "PASS",
        "release_archive_sealed": status == "PASS",
        "release_candidate_closed": status == "PASS",
        "network_allowed": False,
        "broker_connected": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "next_phase": NEXT_PHASE if status == "PASS"
                      else "REPAIR_V76_18_CLOSURE_CERTIFICATE",
    }
    immutable = {
        key: value for key, value in result.items()
        if key not in {"issued_at_utc", "duration_seconds"}
    }
    result["closure_certificate_sha256"] = digest(immutable)
    return result


def summary_from(result: dict[str, Any]) -> dict[str, Any]:
    cert = result["certificate_result"]
    return {
        "status": result["status"],
        "decision": result["decision"],
        "framework_commit_sha": result["repository"]["framework_commit_sha"],
        "closure_certificate_sha256": result["closure_certificate_sha256"],
        "closure_chain_sha256": result["closure_chain_sha256"],
        **result["closure_chain"],
        "gate_count": cert["gate_count"],
        "passed_gate_count": cert["passed_gate_count"],
        "failed_gate_count": cert["failed_gate_count"],
        "failed_gate_ids": cert["failed_gate_ids"],
        "release_archive_closure_certified":
            result["release_archive_closure_certified"],
        "release_archive_independently_verified":
            result["release_archive_independently_verified"],
        "release_archive_sealed": result["release_archive_sealed"],
        "release_candidate_closed": result["release_candidate_closed"],
        "network_allowed": result["network_allowed"],
        "orders_submitted": result["orders_submitted"],
        "approved_for_live": result["approved_for_live"],
        "live_trading_authorized": result["live_trading_authorized"],
        "next_phase": result["next_phase"],
    }


def render_text(result: dict[str, Any]) -> str:
    return "\n".join(
        ["V76.18 RELEASE ARCHIVE CLOSURE CERTIFICATE"] +
        [f"{key}: {value}" for key, value in summary_from(result).items()]
    ) + "\n"


def write_outputs(result: dict[str, Any], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "release_archive_closure_certificate_v76_18.json"
    summary_path = output_dir / "release_archive_closure_certificate_summary_v76_18.json"
    text_path = output_dir / "release_archive_closure_certificate_v76_18.txt"
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8"
    )
    summary_path.write_text(
        json.dumps(summary_from(result), indent=2, sort_keys=True,
                   ensure_ascii=False) + "\n",
        encoding="utf-8"
    )
    text_path.write_text(render_text(result), encoding="utf-8")
    return [result_path, summary_path, text_path]


def cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    result = create_closure_certificate(
        Path(args.repository_root),
        load_json(Path(args.config)),
    )
    outputs = write_outputs(result, Path(args.output_dir))
    cert = result["certificate_result"]
    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "gate_count": cert["gate_count"],
        "passed_gate_count": cert["passed_gate_count"],
        "failed_gate_count": cert["failed_gate_count"],
        "failed_gate_ids": cert["failed_gate_ids"],
        "release_archive_closure_certified":
            result["release_archive_closure_certified"],
        "release_archive_independently_verified":
            result["release_archive_independently_verified"],
        "release_archive_sealed": result["release_archive_sealed"],
        "release_candidate_closed": result["release_candidate_closed"],
        "closure_certificate_sha256": result["closure_certificate_sha256"],
        "closure_chain_sha256": result["closure_chain_sha256"],
        **result["closure_chain"],
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
