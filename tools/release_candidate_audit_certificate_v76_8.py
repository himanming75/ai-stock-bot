from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "76.8"
SCHEMA = "v76.8.release_candidate_audit_certificate.1"


class CertificateError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CertificateError(f"required JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CertificateError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise CertificateError(f"JSON root must be an object: {path}")
    return value


def validate_sha256(value: Any, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise CertificateError(f"{name} must be a 64-character SHA256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise CertificateError(f"{name} must be hexadecimal") from exc


def validate_commit(value: Any, name: str) -> None:
    if not isinstance(value, str) or len(value) != 40:
        raise CertificateError(f"{name} must be a 40-character Git SHA")
    try:
        int(value, 16)
    except ValueError as exc:
        raise CertificateError(f"{name} must be hexadecimal") from exc


def validate_config(config: dict[str, Any]) -> None:
    if config.get("certificate_scope") != "RELEASE_CANDIDATE_AUDIT_CERTIFICATE":
        raise CertificateError("certificate_scope invalid")

    for key in (
        "offline_only",
        "require_git_tracked_clean",
        "require_head_matches_origin_main",
        "require_v76_7_audit_pass",
        "require_all_anchored_hashes_match",
        "require_zero_trading_side_effects",
    ):
        if config.get(key) is not True:
            raise CertificateError(f"{key} must be true")

    for key in (
        "network_allowed",
        "broker_connection_allowed",
        "order_submission_allowed",
        "live_trading_allowed",
        "live_approval_allowed",
    ):
        if config.get(key) is not False:
            raise CertificateError(f"{key} must be false")

    validate_commit(config.get("expected_framework_commit_sha"),
                    "expected_framework_commit_sha")
    validate_commit(config.get("expected_v76_6_sealed_commit_sha"),
                    "expected_v76_6_sealed_commit_sha")

    expected = config.get("expected_hashes")
    if not isinstance(expected, dict):
        raise CertificateError("expected_hashes must be an object")
    for key in (
        "v76_7_audit_sha256",
        "v76_6_manifest_sha256",
        "v76_6_ledger_sha256",
        "v76_6_certificate_sha256",
        "v76_6_release_seal_sha256",
    ):
        validate_sha256(expected.get(key), f"expected_hashes.{key}")

    for key in ("v76_7_output_dir", "v76_6_output_dir"):
        if not isinstance(config.get(key), str) or not config[key]:
            raise CertificateError(f"{key} required")


def safe_relative(root: Path, relative_text: str) -> Path:
    relative = Path(relative_text)
    if relative.is_absolute() or ".." in relative.parts:
        raise CertificateError(f"unsafe relative path: {relative_text}")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise CertificateError(f"path outside repository: {relative_text}") from exc
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
        raise CertificateError(
            f"git {' '.join(args)} failed: {completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def git_state(root: Path) -> dict[str, Any]:
    tracked_status = run_git(root, ["status", "--short", "--untracked-files=no"])
    full_status = run_git(root, ["status", "--short"])
    return {
        "head_sha": run_git(root, ["rev-parse", "HEAD"]),
        "origin_main_sha": run_git(root, ["rev-parse", "origin/main"]),
        "branch": run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"]),
        "tracked_status_short":
            tracked_status.splitlines() if tracked_status else [],
        "full_status_short":
            full_status.splitlines() if full_status else [],
    }


def internal_hash_valid(value: dict[str, Any], field: str) -> tuple[bool, Any, str]:
    stored = value.get(field)
    calculated = digest({
        key: item for key, item in value.items()
        if key != field
    })
    return stored == calculated, stored, calculated


def add_gate(
    gates: list[dict[str, Any]],
    gate_id: str,
    passed: bool,
    **details: Any,
) -> None:
    gate = {
        "gate_id": gate_id,
        "status": "PASS" if passed else "FAIL",
    }
    gate.update(details)
    gates.append(gate)


def create_certificate(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    validate_config(config)
    started = time.time()

    v76_7_dir = safe_relative(root, config["v76_7_output_dir"])
    v76_6_dir = safe_relative(root, config["v76_6_output_dir"])

    audit_path = v76_7_dir / "release_candidate_seal_verification_v76_7.json"
    audit_summary_path = (
        v76_7_dir / "release_candidate_seal_verification_summary_v76_7.json"
    )
    manifest_path = (
        v76_6_dir / "release_candidate_evidence_manifest_v76_6.json"
    )
    ledger_path = (
        v76_6_dir / "release_candidate_evidence_ledger_v76_6.json"
    )
    prior_certificate_path = (
        v76_6_dir / "release_candidate_certificate_v76_6.json"
    )
    seal_result_path = (
        v76_6_dir / "release_candidate_evidence_seal_v76_6.json"
    )

    audit = load_json(audit_path)
    audit_summary = load_json(audit_summary_path)
    manifest = load_json(manifest_path)
    ledger = load_json(ledger_path)
    prior_certificate = load_json(prior_certificate_path)
    seal_result = load_json(seal_result_path)

    expected = config["expected_hashes"]
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
        "GIT_HEAD_MATCHES_V76_7_FRAMEWORK_COMMIT",
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

    audit_valid, audit_stored, audit_calculated = internal_hash_valid(
        audit, "audit_sha256"
    )
    add_gate(
        gates,
        "V76_7_AUDIT_INTERNAL_HASH",
        audit_valid,
        stored=audit_stored,
        calculated=audit_calculated,
    )
    add_gate(
        gates,
        "V76_7_AUDIT_HASH_ANCHORED",
        audit.get("audit_sha256") == expected["v76_7_audit_sha256"],
        actual=audit.get("audit_sha256"),
        expected=expected["v76_7_audit_sha256"],
    )
    add_gate(
        gates,
        "V76_7_AUDIT_STATUS_PASS",
        audit.get("status") == "PASS",
        actual=audit.get("status"),
        expected="PASS",
    )
    add_gate(
        gates,
        "V76_7_INDEPENDENT_VERIFICATION_TRUE",
        audit.get("independent_verification_passed") is True,
        actual=audit.get("independent_verification_passed"),
        expected=True,
    )
    add_gate(
        gates,
        "V76_7_FAILED_GATE_COUNT_ZERO",
        audit.get("failed_gate_count") == 0,
        actual=audit.get("failed_gate_count"),
        expected=0,
    )
    add_gate(
        gates,
        "V76_7_ALL_GATES_PASSED",
        audit.get("passed_gate_count") == audit.get("gate_count"),
        actual=audit.get("passed_gate_count"),
        expected=audit.get("gate_count"),
    )
    add_gate(
        gates,
        "V76_7_SUMMARY_AUDIT_HASH_REFERENCE",
        audit_summary.get("audit_sha256") == audit.get("audit_sha256"),
        actual=audit_summary.get("audit_sha256"),
        expected=audit.get("audit_sha256"),
    )

    anchors = {
        "V76_6_MANIFEST_HASH":
            (manifest.get("manifest_sha256"),
             expected["v76_6_manifest_sha256"]),
        "V76_6_LEDGER_HASH":
            (ledger.get("ledger_sha256"),
             expected["v76_6_ledger_sha256"]),
        "V76_6_CERTIFICATE_HASH":
            (prior_certificate.get("certificate_sha256"),
             expected["v76_6_certificate_sha256"]),
        "V76_6_RELEASE_SEAL_HASH":
            (prior_certificate.get("release_seal_sha256"),
             expected["v76_6_release_seal_sha256"]),
    }
    for gate_id, (actual, expected_value) in anchors.items():
        add_gate(
            gates,
            gate_id,
            actual == expected_value,
            actual=actual,
            expected=expected_value,
        )

    add_gate(
        gates,
        "AUDIT_MANIFEST_REFERENCE",
        audit.get("manifest_sha256") == manifest.get("manifest_sha256"),
        actual=audit.get("manifest_sha256"),
        expected=manifest.get("manifest_sha256"),
    )
    add_gate(
        gates,
        "AUDIT_LEDGER_REFERENCE",
        audit.get("ledger_sha256") == ledger.get("ledger_sha256"),
        actual=audit.get("ledger_sha256"),
        expected=ledger.get("ledger_sha256"),
    )
    add_gate(
        gates,
        "AUDIT_CERTIFICATE_REFERENCE",
        audit.get("certificate_sha256")
        == prior_certificate.get("certificate_sha256"),
        actual=audit.get("certificate_sha256"),
        expected=prior_certificate.get("certificate_sha256"),
    )
    add_gate(
        gates,
        "AUDIT_RELEASE_SEAL_REFERENCE",
        audit.get("release_seal_sha256")
        == prior_certificate.get("release_seal_sha256"),
        actual=audit.get("release_seal_sha256"),
        expected=prior_certificate.get("release_seal_sha256"),
    )
    add_gate(
        gates,
        "V76_6_SEALED_COMMIT_REFERENCE",
        audit.get("expected_sealed_commit_sha")
        == config["expected_v76_6_sealed_commit_sha"],
        actual=audit.get("expected_sealed_commit_sha"),
        expected=config["expected_v76_6_sealed_commit_sha"],
    )
    add_gate(
        gates,
        "SEAL_RESULT_CERTIFICATE_REFERENCE",
        seal_result.get("certificate_sha256")
        == prior_certificate.get("certificate_sha256"),
        actual=seal_result.get("certificate_sha256"),
        expected=prior_certificate.get("certificate_sha256"),
    )

    safety_checks = {
        "AUDIT_NETWORK_FALSE": audit.get("network_allowed") is False,
        "AUDIT_ORDERS_ZERO": audit.get("orders_submitted") == 0,
        "AUDIT_LIVE_APPROVAL_FALSE": audit.get("approved_for_live") is False,
        "PRIOR_CERTIFICATE_NETWORK_FALSE":
            prior_certificate.get("network_allowed") is False,
        "PRIOR_CERTIFICATE_ORDERS_ZERO":
            prior_certificate.get("orders_submitted") == 0,
        "PRIOR_CERTIFICATE_LIVE_APPROVAL_FALSE":
            prior_certificate.get("approved_for_live") is False,
        "SEAL_RESULT_NETWORK_FALSE":
            seal_result.get("network_allowed") is False,
        "SEAL_RESULT_ORDERS_ZERO":
            seal_result.get("orders_submitted") == 0,
        "SEAL_RESULT_LIVE_APPROVAL_FALSE":
            seal_result.get("approved_for_live") is False,
    }
    for gate_id, passed in safety_checks.items():
        add_gate(gates, gate_id, passed)

    failed = [gate["gate_id"] for gate in gates if gate["status"] != "PASS"]
    status = "PASS" if not failed else "FAIL"
    issued_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    certificate = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "certificate_type": "RELEASE_CANDIDATE_AUDIT_CERTIFICATE",
        "status": status,
        "decision": (
            "release_candidate_audit_certificate_issued"
            if status == "PASS"
            else "release_candidate_audit_certificate_withheld"
        ),
        "issued_at_utc": issued_at,
        "issuer": {
            "system": "ai-stock-bot-offline-audit",
            "tool": "release_candidate_audit_certificate_v76_8.py",
            "version": VERSION,
        },
        "repository": {
            "branch": git["branch"],
            "framework_commit_sha": git["head_sha"],
            "origin_main_sha": git["origin_main_sha"],
            "v76_6_sealed_commit_sha":
                config["expected_v76_6_sealed_commit_sha"],
            "tracked_working_tree_clean":
                git["tracked_status_short"] == [],
        },
        "anchored_artifacts": {
            "v76_7_audit_sha256": audit.get("audit_sha256"),
            "v76_6_manifest_sha256": manifest.get("manifest_sha256"),
            "v76_6_ledger_sha256": ledger.get("ledger_sha256"),
            "v76_6_certificate_sha256":
                prior_certificate.get("certificate_sha256"),
            "v76_6_release_seal_sha256":
                prior_certificate.get("release_seal_sha256"),
        },
        "audit_result": {
            "gate_count": len(gates),
            "passed_gate_count": len(gates) - len(failed),
            "failed_gate_count": len(failed),
            "failed_gate_ids": failed,
            "gates": gates,
        },
        "release_candidate_audit_certified": status == "PASS",
        "independent_verification_passed":
            audit.get("independent_verification_passed") is True,
        "network_allowed": False,
        "broker_connected": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "duration_seconds": round(time.time() - started, 6),
        "next_phase": (
            "V76_9_RELEASE_CANDIDATE_AUDIT_CERTIFICATE_VERIFICATION"
            if status == "PASS"
            else "REPAIR_V76_7_RELEASE_CANDIDATE_VERIFICATION"
        ),
    }
    certificate["audit_certificate_sha256"] = digest(certificate)
    return certificate


def certificate_text(certificate: dict[str, Any]) -> str:
    anchors = certificate["anchored_artifacts"]
    audit = certificate["audit_result"]
    repository = certificate["repository"]
    return "\n".join([
        "AI STOCK BOT V76.8 RELEASE CANDIDATE AUDIT CERTIFICATE",
        "=" * 65,
        f"Status                         : {certificate['status']}",
        f"Decision                       : {certificate['decision']}",
        f"Issued At UTC                  : {certificate['issued_at_utc']}",
        f"Framework Commit               : {repository['framework_commit_sha']}",
        f"V76.6 Sealed Commit            : {repository['v76_6_sealed_commit_sha']}",
        f"V76.7 Audit SHA256             : {anchors['v76_7_audit_sha256']}",
        f"V76.6 Manifest SHA256          : {anchors['v76_6_manifest_sha256']}",
        f"V76.6 Ledger SHA256            : {anchors['v76_6_ledger_sha256']}",
        f"V76.6 Certificate SHA256       : {anchors['v76_6_certificate_sha256']}",
        f"V76.6 Release Seal SHA256      : {anchors['v76_6_release_seal_sha256']}",
        f"Audit Certificate SHA256       : {certificate['audit_certificate_sha256']}",
        f"Gate Count                     : {audit['gate_count']}",
        f"Passed Gate Count              : {audit['passed_gate_count']}",
        f"Failed Gate Count              : {audit['failed_gate_count']}",
        f"Audit Certified                : {str(certificate['release_candidate_audit_certified']).lower()}",
        f"Network Allowed                : {str(certificate['network_allowed']).lower()}",
        f"Orders Submitted               : {certificate['orders_submitted']}",
        f"Approved For Live              : {str(certificate['approved_for_live']).lower()}",
        f"Next Phase                     : {certificate['next_phase']}",
        "",
        "This certificate records an offline release candidate audit.",
        "It does not authorize broker connectivity, order submission, or live trading.",
        "",
    ])


def write_outputs(output_dir: Path, certificate: dict[str, Any]) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    certificate_path = (
        output_dir / "release_candidate_audit_certificate_v76_8.json"
    )
    summary_path = (
        output_dir / "release_candidate_audit_certificate_summary_v76_8.json"
    )
    text_path = (
        output_dir / "release_candidate_audit_certificate_v76_8.txt"
    )

    certificate_path.write_text(
        json.dumps(certificate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary = {
        "schema_version": certificate["schema_version"],
        "version": certificate["version"],
        "certificate_type": certificate["certificate_type"],
        "status": certificate["status"],
        "decision": certificate["decision"],
        "issued_at_utc": certificate["issued_at_utc"],
        "framework_commit_sha":
            certificate["repository"]["framework_commit_sha"],
        "v76_6_sealed_commit_sha":
            certificate["repository"]["v76_6_sealed_commit_sha"],
        **certificate["anchored_artifacts"],
        "audit_certificate_sha256":
            certificate["audit_certificate_sha256"],
        "gate_count": certificate["audit_result"]["gate_count"],
        "passed_gate_count":
            certificate["audit_result"]["passed_gate_count"],
        "failed_gate_count":
            certificate["audit_result"]["failed_gate_count"],
        "failed_gate_ids":
            certificate["audit_result"]["failed_gate_ids"],
        "release_candidate_audit_certified":
            certificate["release_candidate_audit_certified"],
        "network_allowed": certificate["network_allowed"],
        "orders_submitted": certificate["orders_submitted"],
        "approved_for_live": certificate["approved_for_live"],
        "next_phase": certificate["next_phase"],
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    text_path.write_text(certificate_text(certificate), encoding="utf-8")
    return [certificate_path, summary_path, text_path]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    try:
        config = load_json(Path(args.config))
        certificate = create_certificate(Path(args.repository_root), config)
        outputs = write_outputs(Path(args.output_dir), certificate)
    except (CertificateError, OSError, ValueError) as exc:
        print(json.dumps({
            "status": "ERROR",
            "error": str(exc),
            "approved_for_live": False,
        }, indent=2, sort_keys=True))
        return 2

    print(json.dumps({
        "status": certificate["status"],
        "decision": certificate["decision"],
        "release_candidate_audit_certified":
            certificate["release_candidate_audit_certified"],
        "gate_count": certificate["audit_result"]["gate_count"],
        "passed_gate_count":
            certificate["audit_result"]["passed_gate_count"],
        "failed_gate_count":
            certificate["audit_result"]["failed_gate_count"],
        "failed_gate_ids":
            certificate["audit_result"]["failed_gate_ids"],
        "audit_certificate_sha256":
            certificate["audit_certificate_sha256"],
        "network_allowed": certificate["network_allowed"],
        "orders_submitted": certificate["orders_submitted"],
        "approved_for_live": certificate["approved_for_live"],
        "next_phase": certificate["next_phase"],
        "outputs": [str(path) for path in outputs],
    }, indent=2, sort_keys=True))
    return 0 if certificate["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
