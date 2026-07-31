from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path
from typing import Any

VERSION = "76.7"
SCHEMA = "v76.7.release_candidate_seal_verification.1"


class AuditError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AuditError(f"required JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AuditError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise AuditError(f"JSON root must be object: {path}")
    return value


def validate_sha256(value: Any, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise AuditError(f"{name} must be a 64-character SHA256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise AuditError(f"{name} must be hexadecimal") from exc


def validate_config(config: dict[str, Any]) -> None:
    if config.get("verification_scope") != "RELEASE_CANDIDATE_SEAL_VERIFICATION":
        raise AuditError("verification_scope invalid")

    for key in (
        "offline_only",
        "require_git_clean",
        "require_head_matches_origin_main",
        "require_sealed_commit_match",
        "require_all_hashes_match",
        "require_all_evidence_files_match",
        "require_zero_trading_side_effects",
    ):
        if config.get(key) is not True:
            raise AuditError(f"{key} must be true")

    for key in (
        "network_allowed",
        "broker_connection_allowed",
        "order_submission_allowed",
        "live_trading_allowed",
        "live_approval_allowed",
    ):
        if config.get(key) is not False:
            raise AuditError(f"{key} must be false")

    sealed_commit = config.get("expected_sealed_commit_sha")
    if not isinstance(sealed_commit, str) or len(sealed_commit) != 40:
        raise AuditError("expected_sealed_commit_sha must be a 40-character commit SHA")

    expected = config.get("expected_hashes")
    if not isinstance(expected, dict):
        raise AuditError("expected_hashes must be an object")
    for key in (
        "manifest_sha256",
        "ledger_sha256",
        "certificate_sha256",
        "release_seal_sha256",
    ):
        validate_sha256(expected.get(key), f"expected_hashes.{key}")

    output_dir = config.get("v76_6_output_dir")
    if not isinstance(output_dir, str) or not output_dir:
        raise AuditError("v76_6_output_dir required")


def safe_relative(root: Path, relative_text: str) -> Path:
    relative = Path(relative_text)
    if relative.is_absolute() or ".." in relative.parts:
        raise AuditError(f"unsafe relative path: {relative_text}")
    path = (root / relative).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise AuditError(f"path outside repository: {relative_text}") from exc
    return path


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
        raise AuditError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def git_state(root: Path) -> dict[str, Any]:
    # Seal verification must reject tracked or staged mutations, but V76.7 is
    # intentionally executed before its own framework is committed. Therefore
    # untracked V76.7 installer/output files are reported separately and do not
    # invalidate the already sealed V76.6 commit.
    tracked_status = run_git(
        root,
        ["status", "--short", "--untracked-files=no"],
    )
    full_status = run_git(root, ["status", "--short"])
    return {
        "head_sha": run_git(root, ["rev-parse", "HEAD"]),
        "origin_main_sha": run_git(root, ["rev-parse", "origin/main"]),
        "branch": run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"]),
        "tracked_status_short":
            tracked_status.splitlines() if tracked_status else [],
        "untracked_or_full_status_short":
            full_status.splitlines() if full_status else [],
    }


def verify_hash_field(
    gates: list[dict[str, Any]],
    gate_id: str,
    actual: Any,
    expected: Any,
) -> None:
    passed = actual == expected
    gates.append({
        "gate_id": gate_id,
        "status": "PASS" if passed else "FAIL",
        "actual": actual,
        "expected": expected,
    })


def verify_ledger_chain(ledger: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    entries = ledger.get("entries")
    if not isinstance(entries, list):
        return False, ["entries must be a list"]

    previous = "0" * 64
    for sequence, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            errors.append(f"entry {sequence} is not an object")
            continue
        if entry.get("sequence") != sequence:
            errors.append(f"sequence mismatch at {sequence}")
        if entry.get("previous_entry_sha256") != previous:
            errors.append(f"previous hash mismatch at {sequence}")
        calculated = digest({
            key: value for key, value in entry.items()
            if key != "entry_sha256"
        })
        if entry.get("entry_sha256") != calculated:
            errors.append(f"entry hash mismatch at {sequence}")
        previous = entry.get("entry_sha256")

    if entries and ledger.get("ledger_head_sha256") != entries[-1].get("entry_sha256"):
        errors.append("ledger head mismatch")
    return not errors, errors


def verify_internal_object_hash(
    value: dict[str, Any],
    hash_field: str,
) -> tuple[bool, Any, str]:
    stored = value.get(hash_field)
    calculated = digest({
        key: item for key, item in value.items()
        if key != hash_field
    })
    return stored == calculated, stored, calculated


def execute_audit(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    validate_config(config)
    started = time.time()

    output_dir = safe_relative(root, config["v76_6_output_dir"])
    paths = {
        "manifest": output_dir / "release_candidate_evidence_manifest_v76_6.json",
        "ledger": output_dir / "release_candidate_evidence_ledger_v76_6.json",
        "certificate": output_dir / "release_candidate_certificate_v76_6.json",
        "seal_result": output_dir / "release_candidate_evidence_seal_v76_6.json",
    }
    objects = {name: load_json(path) for name, path in paths.items()}
    manifest = objects["manifest"]
    ledger = objects["ledger"]
    certificate = objects["certificate"]
    seal_result = objects["seal_result"]

    gates: list[dict[str, Any]] = []
    git = git_state(root)
    expected = config["expected_hashes"]

    verify_hash_field(gates, "GIT_HEAD_MATCHES_ORIGIN_MAIN",
                      git["head_sha"], git["origin_main_sha"])
    verify_hash_field(gates, "GIT_HEAD_MATCHES_SEALED_COMMIT",
                      git["head_sha"], config["expected_sealed_commit_sha"])
    verify_hash_field(gates, "GIT_TRACKED_WORKING_TREE_CLEAN",
                      git["tracked_status_short"], [])

    for object_name, hash_field in (
        ("manifest", "manifest_sha256"),
        ("ledger", "ledger_sha256"),
        ("certificate", "certificate_sha256"),
        ("seal_result", "seal_result_sha256"),
    ):
        passed, stored, calculated = verify_internal_object_hash(
            objects[object_name], hash_field
        )
        gates.append({
            "gate_id": f"{object_name.upper()}_INTERNAL_HASH",
            "status": "PASS" if passed else "FAIL",
            "stored": stored,
            "calculated": calculated,
        })

    verify_hash_field(gates, "EXPECTED_MANIFEST_HASH",
                      manifest.get("manifest_sha256"),
                      expected["manifest_sha256"])
    verify_hash_field(gates, "EXPECTED_LEDGER_HASH",
                      ledger.get("ledger_sha256"),
                      expected["ledger_sha256"])
    verify_hash_field(gates, "EXPECTED_CERTIFICATE_HASH",
                      certificate.get("certificate_sha256"),
                      expected["certificate_sha256"])
    verify_hash_field(gates, "EXPECTED_RELEASE_SEAL_HASH",
                      certificate.get("release_seal_sha256"),
                      expected["release_seal_sha256"])

    chain_valid, chain_errors = verify_ledger_chain(ledger)
    gates.append({
        "gate_id": "LEDGER_CHAIN",
        "status": "PASS" if chain_valid else "FAIL",
        "errors": chain_errors,
    })

    reference_checks = {
        "CERTIFICATE_MANIFEST_REFERENCE":
            certificate.get("manifest_sha256") == manifest.get("manifest_sha256"),
        "CERTIFICATE_LEDGER_REFERENCE":
            certificate.get("ledger_sha256") == ledger.get("ledger_sha256"),
        "RESULT_CERTIFICATE_REFERENCE":
            seal_result.get("certificate_sha256") == certificate.get("certificate_sha256"),
        "RESULT_RELEASE_SEAL_REFERENCE":
            seal_result.get("release_seal_sha256") == certificate.get("release_seal_sha256"),
        "CERTIFICATE_REPOSITORY_COMMIT":
            certificate.get("repository", {}).get("commit_sha")
            == config["expected_sealed_commit_sha"],
        "CERTIFICATE_ORIGIN_MAIN":
            certificate.get("repository", {}).get("origin_main_sha")
            == config["expected_sealed_commit_sha"],
    }
    for gate_id, passed in reference_checks.items():
        gates.append({
            "gate_id": gate_id,
            "status": "PASS" if passed else "FAIL",
        })

    safety_checks = {
        "CERTIFICATE_STATUS_PASS": certificate.get("status") == "PASS",
        "CERTIFICATE_SEALED_TRUE":
            certificate.get("release_candidate_sealed") is True,
        "CERTIFICATE_APPROVED_FOR_LIVE_FALSE":
            certificate.get("approved_for_live") is False,
        "CERTIFICATE_NETWORK_FALSE":
            certificate.get("network_allowed") is False,
        "CERTIFICATE_ORDERS_ZERO":
            certificate.get("orders_submitted") == 0,
        "SEAL_RESULT_STATUS_PASS": seal_result.get("status") == "PASS",
        "SEAL_RESULT_APPROVED_FOR_LIVE_FALSE":
            seal_result.get("approved_for_live") is False,
        "SEAL_RESULT_NETWORK_FALSE":
            seal_result.get("network_allowed") is False,
        "SEAL_RESULT_ORDERS_ZERO":
            seal_result.get("orders_submitted") == 0,
    }
    for gate_id, passed in safety_checks.items():
        gates.append({
            "gate_id": gate_id,
            "status": "PASS" if passed else "FAIL",
        })

    evidence_errors: list[str] = []
    evidence = manifest.get("evidence")
    if not isinstance(evidence, list):
        evidence_errors.append("manifest evidence must be a list")
        evidence = []
    for item in evidence:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            evidence_errors.append("invalid evidence record")
            continue
        evidence_path = safe_relative(root, item["path"])
        if not evidence_path.is_file():
            evidence_errors.append(f"missing: {item['path']}")
            continue
        actual = file_sha256(evidence_path)
        if actual != item.get("file_sha256"):
            evidence_errors.append(f"hash mismatch: {item['path']}")
        if item.get("status") != "PASS":
            evidence_errors.append(f"status not PASS: {item['path']}")
    gates.append({
        "gate_id": "ALL_EVIDENCE_FILES_MATCH",
        "status": "PASS" if not evidence_errors else "FAIL",
        "evidence_count": len(evidence),
        "errors": evidence_errors,
    })

    failed = [gate["gate_id"] for gate in gates if gate["status"] != "PASS"]
    status = "PASS" if not failed else "FAIL"
    audit_core = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "status": status,
        "decision": (
            "release_candidate_seal_independently_verified"
            if status == "PASS"
            else "release_candidate_seal_verification_failed"
        ),
        "gate_count": len(gates),
        "passed_gate_count": len(gates) - len(failed),
        "failed_gate_count": len(failed),
        "failed_gate_ids": failed,
        "gates": gates,
        "git": git,
        "expected_sealed_commit_sha": config["expected_sealed_commit_sha"],
        "manifest_sha256": manifest.get("manifest_sha256"),
        "ledger_sha256": ledger.get("ledger_sha256"),
        "certificate_sha256": certificate.get("certificate_sha256"),
        "release_seal_sha256": certificate.get("release_seal_sha256"),
        "evidence_count": len(evidence),
        "independent_verification_passed": status == "PASS",
        "network_allowed": False,
        "broker_connected": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "next_phase": (
            "V76_8_RELEASE_CANDIDATE_AUDIT_CERTIFICATE"
            if status == "PASS"
            else "REPAIR_V76_6_RELEASE_CANDIDATE_SEAL"
        ),
        "duration_seconds": round(time.time() - started, 6),
    }
    audit_core["audit_sha256"] = digest(audit_core)
    return audit_core


def report_text(result: dict[str, Any]) -> str:
    return "\n".join([
        "AI STOCK BOT V76.7 RELEASE CANDIDATE SEAL VERIFICATION",
        "=" * 63,
        f"Status                         : {result['status']}",
        f"Decision                       : {result['decision']}",
        f"Gate Count                     : {result['gate_count']}",
        f"Passed Gate Count              : {result['passed_gate_count']}",
        f"Failed Gate Count              : {result['failed_gate_count']}",
        f"Independent Verification       : {str(result['independent_verification_passed']).lower()}",
        f"Expected Sealed Commit          : {result['expected_sealed_commit_sha']}",
        f"Manifest SHA256                : {result['manifest_sha256']}",
        f"Ledger SHA256                  : {result['ledger_sha256']}",
        f"Certificate SHA256             : {result['certificate_sha256']}",
        f"Release Seal SHA256            : {result['release_seal_sha256']}",
        f"Audit SHA256                   : {result['audit_sha256']}",
        f"Orders Submitted               : {result['orders_submitted']}",
        f"Network Allowed                : {str(result['network_allowed']).lower()}",
        f"Approved For Live              : {str(result['approved_for_live']).lower()}",
        f"Next Phase                     : {result['next_phase']}",
        "",
        "This audit verifies an offline release candidate seal only.",
        "It does not authorize or enable live trading.",
        "",
    ])


def write_outputs(output_dir: Path, result: dict[str, Any]) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "release_candidate_seal_verification_v76_7.json"
    summary_path = output_dir / "release_candidate_seal_verification_summary_v76_7.json"
    report_path = output_dir / "release_candidate_seal_verification_report_v76_7.txt"

    json_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        key: result[key]
        for key in (
            "schema_version",
            "version",
            "status",
            "decision",
            "gate_count",
            "passed_gate_count",
            "failed_gate_count",
            "failed_gate_ids",
            "expected_sealed_commit_sha",
            "manifest_sha256",
            "ledger_sha256",
            "certificate_sha256",
            "release_seal_sha256",
            "audit_sha256",
            "evidence_count",
            "independent_verification_passed",
            "network_allowed",
            "orders_submitted",
            "approved_for_live",
            "next_phase",
        )
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(report_text(result), encoding="utf-8")
    return [json_path, summary_path, report_path]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    try:
        config = load_json(Path(args.config))
        result = execute_audit(Path(args.repository_root), config)
        outputs = write_outputs(Path(args.output_dir), result)
    except (AuditError, OSError, ValueError) as exc:
        print(json.dumps({
            "status": "ERROR",
            "error": str(exc),
            "approved_for_live": False,
        }, indent=2, sort_keys=True))
        return 2

    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "gate_count": result["gate_count"],
        "passed_gate_count": result["passed_gate_count"],
        "failed_gate_count": result["failed_gate_count"],
        "failed_gate_ids": result["failed_gate_ids"],
        "evidence_count": result["evidence_count"],
        "independent_verification_passed":
            result["independent_verification_passed"],
        "release_seal_sha256": result["release_seal_sha256"],
        "audit_sha256": result["audit_sha256"],
        "network_allowed": result["network_allowed"],
        "orders_submitted": result["orders_submitted"],
        "approved_for_live": result["approved_for_live"],
        "next_phase": result["next_phase"],
        "outputs": [str(path) for path in outputs],
    }, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
