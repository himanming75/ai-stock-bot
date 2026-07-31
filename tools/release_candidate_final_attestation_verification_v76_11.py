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

VERSION = "76.11"
SCHEMA = "v76.11.release_candidate_final_attestation_verification.1"


class VerificationError(ValueError):
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
        raise VerificationError(f"required JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise VerificationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise VerificationError(f"JSON root must be an object: {path}")
    return value


def validate_sha256(value: Any, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise VerificationError(f"{name} must be a 64-character SHA256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise VerificationError(f"{name} must be hexadecimal") from exc


def validate_commit(value: Any, name: str) -> None:
    if not isinstance(value, str) or len(value) != 40:
        raise VerificationError(f"{name} must be a 40-character Git SHA")
    try:
        int(value, 16)
    except ValueError as exc:
        raise VerificationError(f"{name} must be hexadecimal") from exc


def validate_config(config: dict[str, Any]) -> None:
    if config.get("verification_scope") != "FINAL_ATTESTATION_VERIFICATION":
        raise VerificationError("verification_scope invalid")

    required_true = (
        "offline_only",
        "require_git_tracked_clean",
        "require_head_matches_origin_main",
        "require_framework_commit_match",
        "require_attestation_self_hash_match",
        "require_attestation_hash_anchor",
        "require_attestation_summary_match",
        "require_all_attestation_gates_pass",
        "require_attested_chain_complete",
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
            raise VerificationError(f"{key} must be true")
    for key in required_false:
        if config.get(key) is not False:
            raise VerificationError(f"{key} must be false")

    validate_commit(
        config.get("expected_framework_commit_sha"),
        "expected_framework_commit_sha",
    )
    validate_sha256(
        config.get("expected_v76_10_final_attestation_sha256"),
        "expected_v76_10_final_attestation_sha256",
    )
    validate_commit(
        config.get("expected_v76_10_source_framework_commit_sha"),
        "expected_v76_10_source_framework_commit_sha",
    )
    if config.get("expected_v76_10_gate_count") != 36:
        raise VerificationError("expected_v76_10_gate_count must be 36")

    source = config.get("v76_10_output_dir")
    if not isinstance(source, str) or not source:
        raise VerificationError("v76_10_output_dir required")


def safe_relative(root: Path, relative_text: str) -> Path:
    relative = Path(relative_text)
    if relative.is_absolute() or ".." in relative.parts:
        raise VerificationError(f"unsafe relative path: {relative_text}")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise VerificationError(f"path outside repository: {relative_text}") from exc
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
        raise VerificationError(
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


def verify_final_attestation(
    root: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    root = root.resolve()
    validate_config(config)
    started = time.time()

    source_dir = safe_relative(root, config["v76_10_output_dir"])
    attestation_path = (
        source_dir / "release_candidate_final_attestation_v76_10.json"
    )
    summary_path = (
        source_dir / "release_candidate_final_attestation_summary_v76_10.json"
    )
    text_path = (
        source_dir / "release_candidate_final_attestation_v76_10.txt"
    )

    attestation = load_json(attestation_path)
    summary = load_json(summary_path)
    git = git_state(root)
    gates: list[dict[str, Any]] = []

    add_gate(
        gates, "GIT_HEAD_MATCHES_ORIGIN_MAIN",
        git["head_sha"] == git["origin_main_sha"],
        actual=git["head_sha"], expected=git["origin_main_sha"],
    )
    add_gate(
        gates, "GIT_HEAD_MATCHES_V76_10_FRAMEWORK_COMMIT",
        git["head_sha"] == config["expected_framework_commit_sha"],
        actual=git["head_sha"],
        expected=config["expected_framework_commit_sha"],
    )
    add_gate(
        gates, "GIT_TRACKED_WORKING_TREE_CLEAN",
        git["tracked_status_short"] == [],
        actual=git["tracked_status_short"], expected=[],
    )
    add_gate(gates, "V76_10_TEXT_ATTESTATION_EXISTS", text_path.is_file())

    stored_hash = attestation.get("final_attestation_sha256")
    calculated_hash = digest({
        key: value for key, value in attestation.items()
        if key != "final_attestation_sha256"
    })
    add_gate(
        gates, "V76_10_ATTESTATION_SELF_HASH",
        stored_hash == calculated_hash,
        stored=stored_hash, calculated=calculated_hash,
    )
    add_gate(
        gates, "V76_10_ATTESTATION_HASH_ANCHORED",
        stored_hash == config["expected_v76_10_final_attestation_sha256"],
        actual=stored_hash,
        expected=config["expected_v76_10_final_attestation_sha256"],
    )
    add_gate(
        gates, "V76_10_SOURCE_FRAMEWORK_COMMIT_ANCHORED",
        attestation.get("repository", {}).get("framework_commit_sha")
        == config["expected_v76_10_source_framework_commit_sha"],
        actual=attestation.get("repository", {}).get("framework_commit_sha"),
        expected=config["expected_v76_10_source_framework_commit_sha"],
    )

    result_data = attestation.get("attestation_result", {})
    gate_count = result_data.get("gate_count")
    passed_count = result_data.get("passed_gate_count")
    failed_count = result_data.get("failed_gate_count")
    failed_ids = result_data.get("failed_gate_ids")
    source_gates = result_data.get("gates")

    attestation_checks = {
        "V76_10_STATUS_PASS": attestation.get("status") == "PASS",
        "V76_10_DECISION_ISSUED":
            attestation.get("decision")
            == "release_candidate_final_attestation_issued",
        "V76_10_FINALLY_ATTESTED_TRUE":
            attestation.get("release_candidate_finally_attested") is True,
        "V76_10_GATE_COUNT":
            gate_count == config["expected_v76_10_gate_count"],
        "V76_10_PASSED_GATE_COUNT":
            passed_count == config["expected_v76_10_gate_count"],
        "V76_10_FAILED_GATE_COUNT_ZERO": failed_count == 0,
        "V76_10_FAILED_GATE_IDS_EMPTY": failed_ids == [],
        "V76_10_GATE_LIST_PRESENT":
            isinstance(source_gates, list)
            and len(source_gates) == config["expected_v76_10_gate_count"],
        "V76_10_ALL_SOURCE_GATES_PASS":
            isinstance(source_gates, list)
            and all(
                isinstance(gate, dict) and gate.get("status") == "PASS"
                for gate in source_gates
            ),
        "V76_10_NEXT_PHASE":
            attestation.get("next_phase")
            == "V76_11_FINAL_ATTESTATION_VERIFICATION",
    }
    for gate_id, passed in attestation_checks.items():
        add_gate(gates, gate_id, passed)

    chain = attestation.get("attested_chain", {})
    chain_checks = {
        "V76_10_CHAIN_V76_6_SEALED":
            chain.get("v76_6_release_candidate_sealed") is True,
        "V76_10_CHAIN_V76_7_VERIFIED":
            chain.get("v76_7_seal_independently_verified") is True,
        "V76_10_CHAIN_V76_8_CERTIFIED":
            chain.get("v76_8_audit_certified") is True,
        "V76_10_CHAIN_V76_9_VERIFIED":
            chain.get(
                "v76_9_audit_certificate_independently_verified"
            ) is True,
    }
    for gate_id, passed in chain_checks.items():
        add_gate(gates, gate_id, passed)

    summary_checks = {
        "V76_10_SUMMARY_STATUS":
            summary.get("status") == attestation.get("status"),
        "V76_10_SUMMARY_DECISION":
            summary.get("decision") == attestation.get("decision"),
        # V76.10 was executed before its source/config commit was created.
        # Therefore its recorded framework commit is the prior V76.9 commit,
        # while V76.11 itself runs at the committed V76.10 framework commit.
        "V76_10_SUMMARY_FRAMEWORK_COMMIT":
            summary.get("framework_commit_sha")
            == attestation.get("repository", {}).get("framework_commit_sha"),
        "V76_10_SUMMARY_ATTESTATION_HASH":
            summary.get("final_attestation_sha256") == stored_hash,
        "V76_10_SUMMARY_GATE_COUNT":
            summary.get("gate_count") == gate_count,
        "V76_10_SUMMARY_PASSED_GATE_COUNT":
            summary.get("passed_gate_count") == passed_count,
        "V76_10_SUMMARY_FAILED_GATE_COUNT":
            summary.get("failed_gate_count") == failed_count,
        "V76_10_SUMMARY_FAILED_GATE_IDS":
            summary.get("failed_gate_ids") == failed_ids,
        "V76_10_SUMMARY_FINALLY_ATTESTED":
            summary.get("release_candidate_finally_attested") is True,
        "V76_10_SUMMARY_CHAIN":
            summary.get("attested_chain") == chain,
        "V76_10_SUMMARY_ANCHORED_HASHES":
            summary.get("anchored_hashes")
            == attestation.get("anchored_hashes"),
    }
    for gate_id, passed in summary_checks.items():
        add_gate(gates, gate_id, passed)

    safety_checks = {
        "V76_10_NETWORK_FALSE":
            attestation.get("network_allowed") is False,
        "V76_10_BROKER_CONNECTED_FALSE":
            attestation.get("broker_connected") is False,
        "V76_10_ORDERS_ZERO":
            attestation.get("orders_submitted") == 0,
        "V76_10_APPROVED_FOR_LIVE_FALSE":
            attestation.get("approved_for_live") is False,
        "V76_10_LIVE_TRADING_AUTHORIZED_FALSE":
            attestation.get("live_trading_authorized") is False,
        "V76_10_SUMMARY_NETWORK_FALSE":
            summary.get("network_allowed") is False,
        "V76_10_SUMMARY_ORDERS_ZERO":
            summary.get("orders_submitted") == 0,
        "V76_10_SUMMARY_APPROVED_FOR_LIVE_FALSE":
            summary.get("approved_for_live") is False,
        "V76_10_SUMMARY_LIVE_TRADING_AUTHORIZED_FALSE":
            summary.get("live_trading_authorized") is False,
    }
    for gate_id, passed in safety_checks.items():
        add_gate(gates, gate_id, passed)

    failed = [g["gate_id"] for g in gates if g["status"] != "PASS"]
    status = "PASS" if not failed else "FAIL"

    result = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "verification_type":
            "RELEASE_CANDIDATE_FINAL_ATTESTATION_VERIFICATION",
        "status": status,
        "decision": (
            "release_candidate_final_attestation_independently_verified"
            if status == "PASS"
            else "release_candidate_final_attestation_verification_failed"
        ),
        "verified_at_utc":
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "repository": {
            "branch": git["branch"],
            "framework_commit_sha": git["head_sha"],
            "origin_main_sha": git["origin_main_sha"],
            "tracked_working_tree_clean":
                git["tracked_status_short"] == [],
        },
        "source_attestation": {
            "final_attestation_sha256": stored_hash,
            "status": attestation.get("status"),
            "decision": attestation.get("decision"),
            "release_candidate_finally_attested":
                attestation.get("release_candidate_finally_attested"),
            "v76_10_gate_count": gate_count,
            "v76_10_passed_gate_count": passed_count,
            "v76_10_failed_gate_count": failed_count,
        },
        "attested_chain": chain,
        "anchored_hashes": attestation.get("anchored_hashes"),
        "verification_result": {
            "gate_count": len(gates),
            "passed_gate_count": len(gates) - len(failed),
            "failed_gate_count": len(failed),
            "failed_gate_ids": failed,
            "gates": gates,
        },
        "final_attestation_independently_verified": status == "PASS",
        "network_allowed": False,
        "broker_connected": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "duration_seconds": round(time.time() - started, 6),
        "next_phase": (
            "V76_12_RELEASE_CANDIDATE_CLOSURE_CERTIFICATE"
            if status == "PASS"
            else "REPAIR_V76_10_FINAL_ATTESTATION"
        ),
    }
    result["verification_sha256"] = digest(result)
    return result


def report_text(result: dict[str, Any]) -> str:
    verification = result["verification_result"]
    source = result["source_attestation"]
    repo = result["repository"]
    return "\n".join([
        "AI STOCK BOT V76.11 FINAL ATTESTATION VERIFICATION",
        "=" * 68,
        f"Status                         : {result['status']}",
        f"Decision                       : {result['decision']}",
        f"Verified At UTC                : {result['verified_at_utc']}",
        f"Framework Commit               : {repo['framework_commit_sha']}",
        f"V76.10 Attestation SHA256      : {source['final_attestation_sha256']}",
        f"V76.10 Attestation Gates       : "
        f"{source['v76_10_passed_gate_count']}/"
        f"{source['v76_10_gate_count']}",
        f"Verification Gates             : "
        f"{verification['passed_gate_count']}/"
        f"{verification['gate_count']}",
        f"Failed Verification Gates      : "
        f"{verification['failed_gate_count']}",
        f"Independently Verified         : "
        f"{str(result['final_attestation_independently_verified']).lower()}",
        f"Verification SHA256            : {result['verification_sha256']}",
        f"Network Allowed                : "
        f"{str(result['network_allowed']).lower()}",
        f"Orders Submitted               : {result['orders_submitted']}",
        f"Approved For Live              : "
        f"{str(result['approved_for_live']).lower()}",
        f"Live Trading Authorized        : "
        f"{str(result['live_trading_authorized']).lower()}",
        f"Next Phase                     : {result['next_phase']}",
        "",
        "This verification confirms the offline release-candidate",
        "attestation chain only. It does not authorize live trading.",
        "",
    ])


def write_outputs(output_dir: Path, result: dict[str, Any]) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = (
        output_dir
        / "release_candidate_final_attestation_verification_v76_11.json"
    )
    summary_path = (
        output_dir
        / "release_candidate_final_attestation_verification_summary_v76_11.json"
    )
    report_path = (
        output_dir
        / "release_candidate_final_attestation_verification_v76_11.txt"
    )

    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    vr = result["verification_result"]
    summary = {
        "schema_version": result["schema_version"],
        "version": result["version"],
        "verification_type": result["verification_type"],
        "status": result["status"],
        "decision": result["decision"],
        "verified_at_utc": result["verified_at_utc"],
        "framework_commit_sha":
            result["repository"]["framework_commit_sha"],
        "final_attestation_sha256":
            result["source_attestation"]["final_attestation_sha256"],
        "verification_sha256": result["verification_sha256"],
        "gate_count": vr["gate_count"],
        "passed_gate_count": vr["passed_gate_count"],
        "failed_gate_count": vr["failed_gate_count"],
        "failed_gate_ids": vr["failed_gate_ids"],
        "final_attestation_independently_verified":
            result["final_attestation_independently_verified"],
        "network_allowed": result["network_allowed"],
        "orders_submitted": result["orders_submitted"],
        "approved_for_live": result["approved_for_live"],
        "live_trading_authorized":
            result["live_trading_authorized"],
        "next_phase": result["next_phase"],
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(report_text(result), encoding="utf-8")
    return [result_path, summary_path, report_path]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    try:
        config = load_json(Path(args.config))
        result = verify_final_attestation(
            Path(args.repository_root), config
        )
        outputs = write_outputs(Path(args.output_dir), result)
    except (VerificationError, OSError, ValueError) as exc:
        print(json.dumps({
            "status": "ERROR",
            "error": str(exc),
            "approved_for_live": False,
            "live_trading_authorized": False,
        }, indent=2, sort_keys=True))
        return 2

    vr = result["verification_result"]
    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "final_attestation_independently_verified":
            result["final_attestation_independently_verified"],
        "gate_count": vr["gate_count"],
        "passed_gate_count": vr["passed_gate_count"],
        "failed_gate_count": vr["failed_gate_count"],
        "failed_gate_ids": vr["failed_gate_ids"],
        "verification_sha256": result["verification_sha256"],
        "network_allowed": result["network_allowed"],
        "orders_submitted": result["orders_submitted"],
        "approved_for_live": result["approved_for_live"],
        "live_trading_authorized":
            result["live_trading_authorized"],
        "next_phase": result["next_phase"],
        "outputs": [str(path) for path in outputs],
    }, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
