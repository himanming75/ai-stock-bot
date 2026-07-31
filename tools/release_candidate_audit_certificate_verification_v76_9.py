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

# Allow both:
#   python tools/release_candidate_audit_certificate_verification_v76_9.py
#   python -m tools.release_candidate_audit_certificate_verification_v76_9
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

VERSION = "76.9"
SCHEMA = "v76.9.release_candidate_audit_certificate_verification.1"


class VerificationError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


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
    if config.get("verification_scope") != "RELEASE_CANDIDATE_AUDIT_CERTIFICATE_VERIFICATION":
        raise VerificationError("verification_scope invalid")

    true_fields = (
        "offline_only",
        "require_git_tracked_clean",
        "require_head_matches_origin_main",
        "require_v76_8_certificate_pass",
        "require_v76_8_self_hash_match",
        "require_v76_8_summary_match",
        "require_all_v76_8_gates_pass",
        "require_zero_trading_side_effects",
    )
    for key in true_fields:
        if config.get(key) is not True:
            raise VerificationError(f"{key} must be true")

    false_fields = (
        "network_allowed",
        "broker_connection_allowed",
        "order_submission_allowed",
        "live_trading_allowed",
        "live_approval_allowed",
    )
    for key in false_fields:
        if config.get(key) is not False:
            raise VerificationError(f"{key} must be false")

    validate_commit(config.get("expected_framework_commit_sha"),
                    "expected_framework_commit_sha")
    validate_sha256(config.get("expected_v76_8_audit_certificate_sha256"),
                    "expected_v76_8_audit_certificate_sha256")

    if config.get("expected_v76_8_gate_count") != 29:
        raise VerificationError("expected_v76_8_gate_count must be 29")

    expected_anchors = config.get("expected_anchors")
    if not isinstance(expected_anchors, dict):
        raise VerificationError("expected_anchors must be an object")
    for key in (
        "v76_7_audit_sha256",
        "v76_6_manifest_sha256",
        "v76_6_ledger_sha256",
        "v76_6_certificate_sha256",
        "v76_6_release_seal_sha256",
    ):
        validate_sha256(expected_anchors.get(key), f"expected_anchors.{key}")

    output_dir = config.get("v76_8_output_dir")
    if not isinstance(output_dir, str) or not output_dir:
        raise VerificationError("v76_8_output_dir required")


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


def verify(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    validate_config(config)
    started = time.time()
    source_dir = safe_relative(root, config["v76_8_output_dir"])

    certificate_path = source_dir / "release_candidate_audit_certificate_v76_8.json"
    summary_path = source_dir / "release_candidate_audit_certificate_summary_v76_8.json"
    text_path = source_dir / "release_candidate_audit_certificate_v76_8.txt"

    certificate = load_json(certificate_path)
    summary = load_json(summary_path)
    text_exists = text_path.is_file()
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
        "GIT_HEAD_MATCHES_V76_8_FRAMEWORK_COMMIT",
        git["head_sha"] == config["expected_framework_commit_sha"],
        actual=git["head_sha"],
        expected=config["expected_framework_commit_sha"],
    )
    add_gate(
        gates,
        "GIT_TRACKED_WORKING_TREE_CLEAN",
        git["tracked_status_short"] == [],
        actual=git["tracked_status_short"],
        expected=[],
    )
    add_gate(gates, "V76_8_TEXT_CERTIFICATE_EXISTS", text_exists)

    stored_hash = certificate.get("audit_certificate_sha256")
    calculated_hash = digest({
        key: value for key, value in certificate.items()
        if key != "audit_certificate_sha256"
    })
    add_gate(
        gates,
        "V76_8_CERTIFICATE_SELF_HASH",
        stored_hash == calculated_hash,
        stored=stored_hash,
        calculated=calculated_hash,
    )
    add_gate(
        gates,
        "V76_8_CERTIFICATE_HASH_ANCHORED",
        stored_hash == config["expected_v76_8_audit_certificate_sha256"],
        actual=stored_hash,
        expected=config["expected_v76_8_audit_certificate_sha256"],
    )
    add_gate(
        gates,
        "V76_8_CERTIFICATE_STATUS_PASS",
        certificate.get("status") == "PASS",
        actual=certificate.get("status"),
        expected="PASS",
    )
    add_gate(
        gates,
        "V76_8_CERTIFICATE_DECISION",
        certificate.get("decision") == "release_candidate_audit_certificate_issued",
        actual=certificate.get("decision"),
        expected="release_candidate_audit_certificate_issued",
    )
    add_gate(
        gates,
        "V76_8_CERTIFIED_TRUE",
        certificate.get("release_candidate_audit_certified") is True,
        actual=certificate.get("release_candidate_audit_certified"),
        expected=True,
    )
    add_gate(
        gates,
        "V76_8_INDEPENDENT_VERIFICATION_TRUE",
        certificate.get("independent_verification_passed") is True,
        actual=certificate.get("independent_verification_passed"),
        expected=True,
    )

    audit_result = certificate.get("audit_result", {})
    gate_count = audit_result.get("gate_count")
    passed_count = audit_result.get("passed_gate_count")
    failed_count = audit_result.get("failed_gate_count")
    failed_ids = audit_result.get("failed_gate_ids")

    add_gate(
        gates,
        "V76_8_GATE_COUNT",
        gate_count == config["expected_v76_8_gate_count"],
        actual=gate_count,
        expected=config["expected_v76_8_gate_count"],
    )
    add_gate(
        gates,
        "V76_8_FAILED_GATE_COUNT_ZERO",
        failed_count == 0,
        actual=failed_count,
        expected=0,
    )
    add_gate(
        gates,
        "V76_8_ALL_GATES_PASSED",
        passed_count == gate_count,
        actual=passed_count,
        expected=gate_count,
    )
    add_gate(
        gates,
        "V76_8_FAILED_GATE_IDS_EMPTY",
        failed_ids == [],
        actual=failed_ids,
        expected=[],
    )

    summary_checks = {
        "V76_8_SUMMARY_STATUS":
            summary.get("status") == certificate.get("status"),
        "V76_8_SUMMARY_DECISION":
            summary.get("decision") == certificate.get("decision"),
        "V76_8_SUMMARY_CERTIFICATE_HASH":
            summary.get("audit_certificate_sha256") == stored_hash,
        "V76_8_SUMMARY_GATE_COUNT":
            summary.get("gate_count") == gate_count,
        "V76_8_SUMMARY_PASSED_GATE_COUNT":
            summary.get("passed_gate_count") == passed_count,
        "V76_8_SUMMARY_FAILED_GATE_COUNT":
            summary.get("failed_gate_count") == failed_count,
        "V76_8_SUMMARY_CERTIFIED":
            summary.get("release_candidate_audit_certified") is True,
    }
    for gate_id, passed in summary_checks.items():
        add_gate(gates, gate_id, passed)

    anchors = certificate.get("anchored_artifacts", {})
    for key, expected in config["expected_anchors"].items():
        actual = anchors.get(key)
        add_gate(
            gates,
            f"V76_8_ANCHOR_{key.upper()}",
            actual == expected,
            actual=actual,
            expected=expected,
        )
        add_gate(
            gates,
            f"V76_8_SUMMARY_ANCHOR_{key.upper()}",
            summary.get(key) == expected,
            actual=summary.get(key),
            expected=expected,
        )

    safety_checks = {
        "V76_8_NETWORK_FALSE": certificate.get("network_allowed") is False,
        "V76_8_BROKER_CONNECTED_FALSE": certificate.get("broker_connected") is False,
        "V76_8_ORDERS_ZERO": certificate.get("orders_submitted") == 0,
        "V76_8_LIVE_APPROVAL_FALSE": certificate.get("approved_for_live") is False,
        "V76_8_SUMMARY_NETWORK_FALSE": summary.get("network_allowed") is False,
        "V76_8_SUMMARY_ORDERS_ZERO": summary.get("orders_submitted") == 0,
        "V76_8_SUMMARY_LIVE_APPROVAL_FALSE": summary.get("approved_for_live") is False,
    }
    for gate_id, passed in safety_checks.items():
        add_gate(gates, gate_id, passed)

    failed = [g["gate_id"] for g in gates if g["status"] != "PASS"]
    status = "PASS" if not failed else "FAIL"
    verified_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    result = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "verification_type": "RELEASE_CANDIDATE_AUDIT_CERTIFICATE_VERIFICATION",
        "status": status,
        "decision": (
            "release_candidate_audit_certificate_independently_verified"
            if status == "PASS"
            else "release_candidate_audit_certificate_verification_failed"
        ),
        "verified_at_utc": verified_at,
        "verifier": {
            "system": "ai-stock-bot-offline-audit",
            "tool": "release_candidate_audit_certificate_verification_v76_9.py",
            "version": VERSION,
        },
        "repository": {
            "branch": git["branch"],
            "framework_commit_sha": git["head_sha"],
            "origin_main_sha": git["origin_main_sha"],
            "tracked_working_tree_clean": git["tracked_status_short"] == [],
        },
        "source_certificate": {
            "audit_certificate_sha256": stored_hash,
            "certificate_status": certificate.get("status"),
            "release_candidate_audit_certified":
                certificate.get("release_candidate_audit_certified"),
            "v76_8_gate_count": gate_count,
            "v76_8_passed_gate_count": passed_count,
            "v76_8_failed_gate_count": failed_count,
        },
        "anchored_artifacts": anchors,
        "verification_result": {
            "gate_count": len(gates),
            "passed_gate_count": len(gates) - len(failed),
            "failed_gate_count": len(failed),
            "failed_gate_ids": failed,
            "gates": gates,
        },
        "audit_certificate_independently_verified": status == "PASS",
        "network_allowed": False,
        "broker_connected": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "duration_seconds": round(time.time() - started, 6),
        "next_phase": (
            "V76_10_RELEASE_CANDIDATE_FINAL_ATTESTATION"
            if status == "PASS"
            else "REPAIR_V76_8_RELEASE_CANDIDATE_AUDIT_CERTIFICATE"
        ),
    }
    result["verification_sha256"] = digest(result)
    return result


def report_text(result: dict[str, Any]) -> str:
    verification = result["verification_result"]
    source = result["source_certificate"]
    repo = result["repository"]
    return "\n".join([
        "AI STOCK BOT V76.9 AUDIT CERTIFICATE VERIFICATION",
        "=" * 65,
        f"Status                         : {result['status']}",
        f"Decision                       : {result['decision']}",
        f"Verified At UTC                : {result['verified_at_utc']}",
        f"Framework Commit               : {repo['framework_commit_sha']}",
        f"V76.8 Certificate SHA256       : {source['audit_certificate_sha256']}",
        f"V76.8 Certificate Gates        : {source['v76_8_passed_gate_count']}/{source['v76_8_gate_count']}",
        f"Verification Gate Count        : {verification['gate_count']}",
        f"Passed Verification Gates      : {verification['passed_gate_count']}",
        f"Failed Verification Gates      : {verification['failed_gate_count']}",
        f"Independently Verified         : {str(result['audit_certificate_independently_verified']).lower()}",
        f"Verification SHA256            : {result['verification_sha256']}",
        f"Network Allowed                : {str(result['network_allowed']).lower()}",
        f"Orders Submitted               : {result['orders_submitted']}",
        f"Approved For Live              : {str(result['approved_for_live']).lower()}",
        f"Next Phase                     : {result['next_phase']}",
        "",
        "This verification remains offline and does not authorize live trading.",
        "",
    ])


def write_outputs(output_dir: Path, result: dict[str, Any]) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "release_candidate_audit_certificate_verification_v76_9.json"
    summary_path = output_dir / "release_candidate_audit_certificate_verification_summary_v76_9.json"
    report_path = output_dir / "release_candidate_audit_certificate_verification_v76_9.txt"

    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "schema_version": result["schema_version"],
        "version": result["version"],
        "verification_type": result["verification_type"],
        "status": result["status"],
        "decision": result["decision"],
        "verified_at_utc": result["verified_at_utc"],
        "framework_commit_sha": result["repository"]["framework_commit_sha"],
        "audit_certificate_sha256":
            result["source_certificate"]["audit_certificate_sha256"],
        "verification_sha256": result["verification_sha256"],
        "gate_count": result["verification_result"]["gate_count"],
        "passed_gate_count": result["verification_result"]["passed_gate_count"],
        "failed_gate_count": result["verification_result"]["failed_gate_count"],
        "failed_gate_ids": result["verification_result"]["failed_gate_ids"],
        "audit_certificate_independently_verified":
            result["audit_certificate_independently_verified"],
        "network_allowed": result["network_allowed"],
        "orders_submitted": result["orders_submitted"],
        "approved_for_live": result["approved_for_live"],
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
        result = verify(Path(args.repository_root), config)
        outputs = write_outputs(Path(args.output_dir), result)
    except (VerificationError, OSError, ValueError) as exc:
        print(json.dumps({
            "status": "ERROR",
            "error": str(exc),
            "approved_for_live": False,
        }, indent=2, sort_keys=True))
        return 2

    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "audit_certificate_independently_verified":
            result["audit_certificate_independently_verified"],
        "gate_count": result["verification_result"]["gate_count"],
        "passed_gate_count": result["verification_result"]["passed_gate_count"],
        "failed_gate_count": result["verification_result"]["failed_gate_count"],
        "failed_gate_ids": result["verification_result"]["failed_gate_ids"],
        "audit_certificate_sha256":
            result["source_certificate"]["audit_certificate_sha256"],
        "verification_sha256": result["verification_sha256"],
        "network_allowed": result["network_allowed"],
        "orders_submitted": result["orders_submitted"],
        "approved_for_live": result["approved_for_live"],
        "next_phase": result["next_phase"],
        "outputs": [str(path) for path in outputs],
    }, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
