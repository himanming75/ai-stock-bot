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

VERSION = "76.12"
SCHEMA = "v76.12.release_candidate_closure_certificate.1"


class ClosureError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ClosureError(f"required JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ClosureError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ClosureError(f"JSON root must be an object: {path}")
    return value


def validate_sha256(value: Any, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ClosureError(f"{name} must be a 64-character SHA256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ClosureError(f"{name} must be hexadecimal") from exc


def validate_commit(value: Any, name: str) -> None:
    if not isinstance(value, str) or len(value) != 40:
        raise ClosureError(f"{name} must be a 40-character Git SHA")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ClosureError(f"{name} must be hexadecimal") from exc


def validate_config(config: dict[str, Any]) -> None:
    if config.get("certificate_scope") != "RELEASE_CANDIDATE_CLOSURE":
        raise ClosureError("certificate_scope invalid")

    required_true = (
        "offline_only",
        "require_git_tracked_clean",
        "require_head_matches_origin_main",
        "require_framework_commit_match",
        "require_v76_11_self_hash_match",
        "require_v76_11_hash_anchor",
        "require_v76_11_summary_match",
        "require_all_v76_11_gates_pass",
        "require_complete_attested_chain",
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
            raise ClosureError(f"{key} must be true")
    for key in required_false:
        if config.get(key) is not False:
            raise ClosureError(f"{key} must be false")

    validate_commit(config.get("expected_framework_commit_sha"),
                    "expected_framework_commit_sha")
    validate_sha256(config.get("expected_v76_11_verification_sha256"),
                    "expected_v76_11_verification_sha256")
    if config.get("expected_v76_11_gate_count") != 41:
        raise ClosureError("expected_v76_11_gate_count must be 41")
    source = config.get("v76_11_output_dir")
    if not isinstance(source, str) or not source:
        raise ClosureError("v76_11_output_dir required")


def safe_relative(root: Path, relative_text: str) -> Path:
    relative = Path(relative_text)
    if relative.is_absolute() or ".." in relative.parts:
        raise ClosureError(f"unsafe relative path: {relative_text}")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ClosureError(f"path outside repository: {relative_text}") from exc
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
        raise ClosureError(
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


def add_gate(gates: list[dict[str, Any]], gate_id: str,
             passed: bool, **details: Any) -> None:
    gate = {"gate_id": gate_id, "status": "PASS" if passed else "FAIL"}
    gate.update(details)
    gates.append(gate)


def issue_closure_certificate(root: Path,
                              config: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    validate_config(config)
    started = time.time()

    source_dir = safe_relative(root, config["v76_11_output_dir"])
    verification_path = source_dir / (
        "release_candidate_final_attestation_verification_v76_11.json"
    )
    summary_path = source_dir / (
        "release_candidate_final_attestation_verification_summary_v76_11.json"
    )
    text_path = source_dir / (
        "release_candidate_final_attestation_verification_v76_11.txt"
    )

    verification = load_json(verification_path)
    summary = load_json(summary_path)
    git = git_state(root)
    gates: list[dict[str, Any]] = []

    add_gate(gates, "GIT_HEAD_MATCHES_ORIGIN_MAIN",
             git["head_sha"] == git["origin_main_sha"],
             actual=git["head_sha"], expected=git["origin_main_sha"])
    add_gate(gates, "GIT_HEAD_MATCHES_V76_11_FRAMEWORK_COMMIT",
             git["head_sha"] == config["expected_framework_commit_sha"],
             actual=git["head_sha"],
             expected=config["expected_framework_commit_sha"])
    add_gate(gates, "GIT_BRANCH_MAIN", git["branch"] == "main",
             actual=git["branch"], expected="main")
    add_gate(gates, "GIT_TRACKED_WORKING_TREE_CLEAN",
             git["tracked_status_short"] == [],
             actual=git["tracked_status_short"], expected=[])
    add_gate(gates, "V76_11_TEXT_VERIFICATION_EXISTS", text_path.is_file())

    stored_hash = verification.get("verification_sha256")
    calculated_hash = digest({
        key: value for key, value in verification.items()
        if key != "verification_sha256"
    })
    add_gate(gates, "V76_11_VERIFICATION_SELF_HASH",
             stored_hash == calculated_hash,
             stored=stored_hash, calculated=calculated_hash)
    add_gate(gates, "V76_11_VERIFICATION_HASH_ANCHORED",
             stored_hash == config["expected_v76_11_verification_sha256"],
             actual=stored_hash,
             expected=config["expected_v76_11_verification_sha256"])

    result_data = verification.get("verification_result", {})
    gate_count = result_data.get("gate_count")
    passed_count = result_data.get("passed_gate_count")
    failed_count = result_data.get("failed_gate_count")
    failed_ids = result_data.get("failed_gate_ids")
    source_gates = result_data.get("gates")

    checks = {
        "V76_11_STATUS_PASS": verification.get("status") == "PASS",
        "V76_11_DECISION_VERIFIED":
            verification.get("decision")
            == "release_candidate_final_attestation_independently_verified",
        "V76_11_INDEPENDENTLY_VERIFIED_TRUE":
            verification.get("final_attestation_independently_verified") is True,
        "V76_11_GATE_COUNT":
            gate_count == config["expected_v76_11_gate_count"],
        "V76_11_PASSED_GATE_COUNT":
            passed_count == config["expected_v76_11_gate_count"],
        "V76_11_FAILED_GATE_COUNT_ZERO": failed_count == 0,
        "V76_11_FAILED_GATE_IDS_EMPTY": failed_ids == [],
        "V76_11_GATE_LIST_PRESENT":
            isinstance(source_gates, list)
            and len(source_gates) == config["expected_v76_11_gate_count"],
        "V76_11_ALL_SOURCE_GATES_PASS":
            isinstance(source_gates, list)
            and all(isinstance(g, dict) and g.get("status") == "PASS"
                    for g in source_gates),
        "V76_11_NEXT_PHASE":
            verification.get("next_phase")
            == "V76_12_RELEASE_CANDIDATE_CLOSURE_CERTIFICATE",
    }
    for gate_id, passed in checks.items():
        add_gate(gates, gate_id, passed)

    summary_checks = {
        "V76_11_SUMMARY_STATUS":
            summary.get("status") == verification.get("status"),
        "V76_11_SUMMARY_DECISION":
            summary.get("decision") == verification.get("decision"),
        "V76_11_SUMMARY_FRAMEWORK_COMMIT":
            summary.get("framework_commit_sha")
            == verification.get("repository", {}).get("framework_commit_sha"),
        "V76_11_SUMMARY_VERIFICATION_HASH":
            summary.get("verification_sha256") == stored_hash,
        "V76_11_SUMMARY_GATE_COUNT":
            summary.get("gate_count") == gate_count,
        "V76_11_SUMMARY_PASSED_GATE_COUNT":
            summary.get("passed_gate_count") == passed_count,
        "V76_11_SUMMARY_FAILED_GATE_COUNT":
            summary.get("failed_gate_count") == failed_count,
        "V76_11_SUMMARY_FAILED_GATE_IDS":
            summary.get("failed_gate_ids") == failed_ids,
        "V76_11_SUMMARY_INDEPENDENTLY_VERIFIED":
            summary.get("final_attestation_independently_verified") is True,
        "V76_11_SUMMARY_NEXT_PHASE":
            summary.get("next_phase")
            == "V76_12_RELEASE_CANDIDATE_CLOSURE_CERTIFICATE",
    }
    for gate_id, passed in summary_checks.items():
        add_gate(gates, gate_id, passed)

    chain = verification.get("attested_chain", {})
    chain_checks = {
        "CHAIN_V76_6_RELEASE_SEALED":
            chain.get("v76_6_release_candidate_sealed") is True,
        "CHAIN_V76_7_SEAL_VERIFIED":
            chain.get("v76_7_seal_independently_verified") is True,
        "CHAIN_V76_8_AUDIT_CERTIFIED":
            chain.get("v76_8_audit_certified") is True,
        "CHAIN_V76_9_AUDIT_VERIFIED":
            chain.get("v76_9_audit_certificate_independently_verified") is True,
    }
    for gate_id, passed in chain_checks.items():
        add_gate(gates, gate_id, passed)

    source_attestation = verification.get("source_attestation", {})
    attestation_checks = {
        "SOURCE_V76_10_STATUS_PASS":
            source_attestation.get("status") == "PASS",
        "SOURCE_V76_10_FINALLY_ATTESTED_TRUE":
            source_attestation.get("release_candidate_finally_attested") is True,
        "SOURCE_V76_10_GATE_COUNT_36":
            source_attestation.get("v76_10_gate_count") == 36,
        "SOURCE_V76_10_PASSED_GATE_COUNT_36":
            source_attestation.get("v76_10_passed_gate_count") == 36,
        "SOURCE_V76_10_FAILED_GATE_COUNT_ZERO":
            source_attestation.get("v76_10_failed_gate_count") == 0,
    }
    for gate_id, passed in attestation_checks.items():
        add_gate(gates, gate_id, passed)

    safety_checks = {
        "V76_11_NETWORK_FALSE":
            verification.get("network_allowed") is False,
        "V76_11_BROKER_CONNECTED_FALSE":
            verification.get("broker_connected") is False,
        "V76_11_ORDERS_ZERO":
            verification.get("orders_submitted") == 0,
        "V76_11_APPROVED_FOR_LIVE_FALSE":
            verification.get("approved_for_live") is False,
        "V76_11_LIVE_TRADING_AUTHORIZED_FALSE":
            verification.get("live_trading_authorized") is False,
        "V76_11_SUMMARY_NETWORK_FALSE":
            summary.get("network_allowed") is False,
        "V76_11_SUMMARY_ORDERS_ZERO":
            summary.get("orders_submitted") == 0,
        "V76_11_SUMMARY_APPROVED_FOR_LIVE_FALSE":
            summary.get("approved_for_live") is False,
        "V76_11_SUMMARY_LIVE_TRADING_AUTHORIZED_FALSE":
            summary.get("live_trading_authorized") is False,
    }
    for gate_id, passed in safety_checks.items():
        add_gate(gates, gate_id, passed)

    failed = [g["gate_id"] for g in gates if g["status"] != "PASS"]
    status = "PASS" if not failed else "FAIL"

    result = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "certificate_type": "RELEASE_CANDIDATE_CLOSURE_CERTIFICATE",
        "status": status,
        "decision": (
            "release_candidate_closure_certificate_issued"
            if status == "PASS"
            else "release_candidate_closure_certificate_failed"
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
        "source_verification": {
            "verification_sha256": stored_hash,
            "status": verification.get("status"),
            "decision": verification.get("decision"),
            "final_attestation_independently_verified":
                verification.get("final_attestation_independently_verified"),
            "v76_11_gate_count": gate_count,
            "v76_11_passed_gate_count": passed_count,
            "v76_11_failed_gate_count": failed_count,
        },
        "attested_chain": chain,
        "anchored_hashes": verification.get("anchored_hashes"),
        "closure_result": {
            "gate_count": len(gates),
            "passed_gate_count": len(gates) - len(failed),
            "failed_gate_count": len(failed),
            "failed_gate_ids": failed,
            "gates": gates,
        },
        "release_candidate_closed": status == "PASS",
        "network_allowed": False,
        "broker_connected": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "duration_seconds": round(time.time() - started, 6),
        "next_phase": (
            "V76_13_RELEASE_CANDIDATE_CLOSURE_VERIFICATION"
            if status == "PASS"
            else "REPAIR_V76_12_RELEASE_CANDIDATE_CLOSURE_CERTIFICATE"
        ),
    }
    result["closure_certificate_sha256"] = digest(result)
    return result


def write_outputs(result: dict[str, Any], output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    cert = output_dir / "release_candidate_closure_certificate_v76_12.json"
    summary = output_dir / (
        "release_candidate_closure_certificate_summary_v76_12.json"
    )
    text = output_dir / "release_candidate_closure_certificate_v76_12.txt"

    cert.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")

    closure = result["closure_result"]
    summary_data = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "status": result["status"],
        "decision": result["decision"],
        "framework_commit_sha":
            result["repository"]["framework_commit_sha"],
        "closure_certificate_sha256":
            result["closure_certificate_sha256"],
        "gate_count": closure["gate_count"],
        "passed_gate_count": closure["passed_gate_count"],
        "failed_gate_count": closure["failed_gate_count"],
        "failed_gate_ids": closure["failed_gate_ids"],
        "release_candidate_closed":
            result["release_candidate_closed"],
        "network_allowed": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "next_phase": result["next_phase"],
    }
    summary.write_text(json.dumps(summary_data, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")

    lines = [
        "V76.12 RELEASE CANDIDATE CLOSURE CERTIFICATE",
        "=" * 48,
        f"Status: {result['status']}",
        f"Decision: {result['decision']}",
        f"Release candidate closed: {result['release_candidate_closed']}",
        f"Gate count: {closure['gate_count']}",
        f"Passed gates: {closure['passed_gate_count']}",
        f"Failed gates: {closure['failed_gate_count']}",
        f"Closure certificate SHA256: "
        f"{result['closure_certificate_sha256']}",
        f"Network allowed: {result['network_allowed']}",
        f"Orders submitted: {result['orders_submitted']}",
        f"Approved for live: {result['approved_for_live']}",
        f"Live trading authorized: "
        f"{result['live_trading_authorized']}",
        f"Next phase: {result['next_phase']}",
    ]
    text.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return [str(cert), str(summary), str(text)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    root = Path(args.repository_root)
    config = load_json(Path(args.config))
    result = issue_closure_certificate(root, config)
    outputs = write_outputs(result, Path(args.output_dir))
    closure = result["closure_result"]

    printed = {
        "approved_for_live": result["approved_for_live"],
        "closure_certificate_sha256":
            result["closure_certificate_sha256"],
        "decision": result["decision"],
        "failed_gate_count": closure["failed_gate_count"],
        "failed_gate_ids": closure["failed_gate_ids"],
        "gate_count": closure["gate_count"],
        "live_trading_authorized":
            result["live_trading_authorized"],
        "network_allowed": result["network_allowed"],
        "next_phase": result["next_phase"],
        "orders_submitted": result["orders_submitted"],
        "outputs": outputs,
        "passed_gate_count": closure["passed_gate_count"],
        "release_candidate_closed":
            result["release_candidate_closed"],
        "status": result["status"],
    }
    print(json.dumps(printed, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
