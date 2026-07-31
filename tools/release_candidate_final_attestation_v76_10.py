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

VERSION = "76.10"
SCHEMA = "v76.10.release_candidate_final_attestation.1"


class AttestationError(ValueError):
    pass


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise AttestationError(f"required JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise AttestationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise AttestationError(f"JSON root must be object: {path}")
    return value


def validate_sha256(value: Any, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise AttestationError(f"{name} must be a 64-character SHA256")
    try:
        int(value, 16)
    except ValueError as exc:
        raise AttestationError(f"{name} must be hexadecimal") from exc


def validate_commit(value: Any, name: str) -> None:
    if not isinstance(value, str) or len(value) != 40:
        raise AttestationError(f"{name} must be a 40-character Git SHA")
    try:
        int(value, 16)
    except ValueError as exc:
        raise AttestationError(f"{name} must be hexadecimal") from exc


def validate_config(config: dict[str, Any]) -> None:
    if config.get("attestation_scope") != "RELEASE_CANDIDATE_FINAL_ATTESTATION":
        raise AttestationError("attestation_scope invalid")

    for key in (
        "offline_only",
        "require_git_tracked_clean",
        "require_head_matches_origin_main",
        "require_v76_6_release_seal",
        "require_v76_7_seal_verification",
        "require_v76_8_audit_certificate",
        "require_v76_9_audit_certificate_verification",
        "require_zero_trading_side_effects",
    ):
        if config.get(key) is not True:
            raise AttestationError(f"{key} must be true")

    for key in (
        "network_allowed",
        "broker_connection_allowed",
        "order_submission_allowed",
        "live_trading_allowed",
        "live_approval_allowed",
    ):
        if config.get(key) is not False:
            raise AttestationError(f"{key} must be false")

    validate_commit(config.get("expected_framework_commit_sha"),
                    "expected_framework_commit_sha")

    expected_hashes = config.get("expected_hashes")
    if not isinstance(expected_hashes, dict):
        raise AttestationError("expected_hashes must be object")
    for key in (
        "v76_6_manifest_sha256",
        "v76_6_ledger_sha256",
        "v76_6_certificate_sha256",
        "v76_6_release_seal_sha256",
        "v76_7_audit_sha256",
        "v76_8_audit_certificate_sha256",
        "v76_9_verification_sha256",
    ):
        validate_sha256(expected_hashes.get(key), f"expected_hashes.{key}")

    for key in ("v76_6_output_dir", "v76_7_output_dir",
                "v76_8_output_dir", "v76_9_output_dir"):
        value = config.get(key)
        if not isinstance(value, str) or not value:
            raise AttestationError(f"{key} required")


def safe_relative(root: Path, relative_text: str) -> Path:
    relative = Path(relative_text)
    if relative.is_absolute() or ".." in relative.parts:
        raise AttestationError(f"unsafe relative path: {relative_text}")
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise AttestationError(f"path outside repository: {relative_text}") from exc
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
        raise AttestationError(
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


def issue_attestation(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    validate_config(config)
    started = time.time()
    expected = config["expected_hashes"]
    git = git_state(root)
    gates: list[dict[str, Any]] = []

    v76_6_dir = safe_relative(root, config["v76_6_output_dir"])
    v76_7_dir = safe_relative(root, config["v76_7_output_dir"])
    v76_8_dir = safe_relative(root, config["v76_8_output_dir"])
    v76_9_dir = safe_relative(root, config["v76_9_output_dir"])

    manifest = load_json(v76_6_dir / "release_candidate_evidence_manifest_v76_6.json")
    ledger = load_json(v76_6_dir / "release_candidate_evidence_ledger_v76_6.json")
    certificate = load_json(v76_6_dir / "release_candidate_certificate_v76_6.json")
    release_seal = load_json(v76_6_dir / "release_candidate_evidence_seal_v76_6.json")
    v76_7 = load_json(v76_7_dir / "release_candidate_seal_verification_v76_7.json")
    v76_8 = load_json(v76_8_dir / "release_candidate_audit_certificate_v76_8.json")
    v76_9 = load_json(v76_9_dir / "release_candidate_audit_certificate_verification_v76_9.json")

    add_gate(gates, "GIT_HEAD_MATCHES_ORIGIN_MAIN",
             git["head_sha"] == git["origin_main_sha"],
             actual=git["head_sha"], expected=git["origin_main_sha"])
    add_gate(gates, "GIT_HEAD_MATCHES_FRAMEWORK_COMMIT",
             git["head_sha"] == config["expected_framework_commit_sha"],
             actual=git["head_sha"], expected=config["expected_framework_commit_sha"])
    add_gate(gates, "GIT_TRACKED_WORKING_TREE_CLEAN",
             git["tracked_status_short"] == [],
             actual=git["tracked_status_short"], expected=[])

    # V76.6 uses two distinct seal hashes:
    # 1. certificate.release_seal_sha256 hashes the original seal_material.
    # 2. seal_result.seal_result_sha256 is the self-hash of the result JSON.
    # Do not treat release_seal_sha256 as the seal-result JSON self-hash.
    actual_hashes = {
        "v76_6_manifest_sha256": digest({
            k: v for k, v in manifest.items() if k != "manifest_sha256"
        }),
        "v76_6_ledger_sha256": digest({
            k: v for k, v in ledger.items() if k != "ledger_sha256"
        }),
        "v76_6_certificate_sha256": digest({
            k: v for k, v in certificate.items() if k != "certificate_sha256"
        }),
        "v76_6_seal_result_sha256": digest({
            k: v for k, v in release_seal.items() if k != "seal_result_sha256"
        }),
        "v76_6_release_seal_sha256": certificate.get("release_seal_sha256"),
        "v76_7_audit_sha256": v76_7.get("audit_sha256"),
        "v76_8_audit_certificate_sha256": v76_8.get("audit_certificate_sha256"),
        "v76_9_verification_sha256": v76_9.get("verification_sha256"),
    }

    stored_hashes = {
        "v76_6_manifest_sha256": manifest.get("manifest_sha256"),
        "v76_6_ledger_sha256": ledger.get("ledger_sha256"),
        "v76_6_certificate_sha256": certificate.get("certificate_sha256"),
        "v76_6_seal_result_sha256": release_seal.get("seal_result_sha256"),
    }

    for key in (
        "v76_6_manifest_sha256",
        "v76_6_ledger_sha256",
        "v76_6_certificate_sha256",
        "v76_6_seal_result_sha256",
    ):
        add_gate(gates, f"{key.upper()}_SELF_HASH",
                 stored_hashes[key] == actual_hashes[key],
                 stored=stored_hashes[key], calculated=actual_hashes[key])

    add_gate(
        gates,
        "V76_6_SEAL_RESULT_CERTIFICATE_REFERENCE",
        release_seal.get("certificate_sha256")
        == certificate.get("certificate_sha256"),
        actual=release_seal.get("certificate_sha256"),
        expected=certificate.get("certificate_sha256"),
    )
    add_gate(
        gates,
        "V76_6_SEAL_RESULT_RELEASE_SEAL_REFERENCE",
        release_seal.get("release_seal_sha256")
        == certificate.get("release_seal_sha256"),
        actual=release_seal.get("release_seal_sha256"),
        expected=certificate.get("release_seal_sha256"),
    )

    for key, expected_hash in expected.items():
        actual = (
            stored_hashes[key]
            if key in stored_hashes
            else actual_hashes[key]
        )
        add_gate(gates, f"{key.upper()}_ANCHORED",
                 actual == expected_hash,
                 actual=actual, expected=expected_hash)

    status_checks = {
        "V76_6_RELEASE_SEAL_PASS": release_seal.get("status") == "PASS",
        "V76_6_RELEASE_CANDIDATE_SEALED":
            release_seal.get("release_candidate_sealed") is True,
        "V76_7_VERIFICATION_PASS": v76_7.get("status") == "PASS",
        "V76_7_INDEPENDENT_VERIFICATION":
            v76_7.get("independent_verification_passed") is True,
        "V76_8_AUDIT_CERTIFICATE_PASS": v76_8.get("status") == "PASS",
        "V76_8_AUDIT_CERTIFIED":
            v76_8.get("release_candidate_audit_certified") is True,
        "V76_9_VERIFICATION_PASS": v76_9.get("status") == "PASS",
        "V76_9_INDEPENDENTLY_VERIFIED":
            v76_9.get("audit_certificate_independently_verified") is True,
    }
    for gate_id, passed in status_checks.items():
        add_gate(gates, gate_id, passed)

    safety_sources = {
        "v76_6_release_seal": release_seal,
        "v76_7_verification": v76_7,
        "v76_8_certificate": v76_8,
        "v76_9_verification": v76_9,
    }
    for source_name, source in safety_sources.items():
        add_gate(gates, f"{source_name.upper()}_NETWORK_FALSE",
                 source.get("network_allowed") is False)
        add_gate(gates, f"{source_name.upper()}_ORDERS_ZERO",
                 source.get("orders_submitted") == 0)
        add_gate(gates, f"{source_name.upper()}_LIVE_APPROVAL_FALSE",
                 source.get("approved_for_live") is False)

    failed = [g["gate_id"] for g in gates if g["status"] != "PASS"]
    status = "PASS" if not failed else "FAIL"
    issued_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    result = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "attestation_type": "RELEASE_CANDIDATE_FINAL_ATTESTATION",
        "status": status,
        "decision": (
            "release_candidate_final_attestation_issued"
            if status == "PASS"
            else "release_candidate_final_attestation_denied"
        ),
        "issued_at_utc": issued_at,
        "repository": {
            "branch": git["branch"],
            "framework_commit_sha": git["head_sha"],
            "origin_main_sha": git["origin_main_sha"],
            "tracked_working_tree_clean": git["tracked_status_short"] == [],
        },
        "attested_chain": {
            "v76_6_release_candidate_sealed":
                release_seal.get("release_candidate_sealed"),
            "v76_7_seal_independently_verified":
                v76_7.get("independent_verification_passed"),
            "v76_8_audit_certified":
                v76_8.get("release_candidate_audit_certified"),
            "v76_9_audit_certificate_independently_verified":
                v76_9.get("audit_certificate_independently_verified"),
        },
        "anchored_hashes": expected,
        "attestation_result": {
            "gate_count": len(gates),
            "passed_gate_count": len(gates) - len(failed),
            "failed_gate_count": len(failed),
            "failed_gate_ids": failed,
            "gates": gates,
        },
        "release_candidate_finally_attested": status == "PASS",
        "network_allowed": False,
        "broker_connected": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "duration_seconds": round(time.time() - started, 6),
        "next_phase": (
            "V76_11_FINAL_ATTESTATION_VERIFICATION"
            if status == "PASS"
            else "REPAIR_RELEASE_CANDIDATE_EVIDENCE_CHAIN"
        ),
    }
    result["final_attestation_sha256"] = digest(result)
    return result


def report_text(result: dict[str, Any]) -> str:
    r = result["attestation_result"]
    repo = result["repository"]
    chain = result["attested_chain"]
    return "\n".join([
        "AI STOCK BOT V76.10 RELEASE CANDIDATE FINAL ATTESTATION",
        "=" * 72,
        f"Status                         : {result['status']}",
        f"Decision                       : {result['decision']}",
        f"Issued At UTC                  : {result['issued_at_utc']}",
        f"Framework Commit               : {repo['framework_commit_sha']}",
        f"V76.6 Sealed                   : {str(chain['v76_6_release_candidate_sealed']).lower()}",
        f"V76.7 Seal Verified            : {str(chain['v76_7_seal_independently_verified']).lower()}",
        f"V76.8 Audit Certified          : {str(chain['v76_8_audit_certified']).lower()}",
        f"V76.9 Audit Verified           : {str(chain['v76_9_audit_certificate_independently_verified']).lower()}",
        f"Attestation Gates              : {r['passed_gate_count']}/{r['gate_count']}",
        f"Failed Gates                   : {r['failed_gate_count']}",
        f"Finally Attested               : {str(result['release_candidate_finally_attested']).lower()}",
        f"Final Attestation SHA256       : {result['final_attestation_sha256']}",
        f"Network Allowed                : {str(result['network_allowed']).lower()}",
        f"Orders Submitted               : {result['orders_submitted']}",
        f"Approved For Live              : {str(result['approved_for_live']).lower()}",
        f"Live Trading Authorized        : {str(result['live_trading_authorized']).lower()}",
        f"Next Phase                     : {result['next_phase']}",
        "",
        "This attestation proves release-candidate evidence integrity only.",
        "It does not authorize broker connectivity or live order submission.",
        "",
    ])


def write_outputs(output_dir: Path, result: dict[str, Any]) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "release_candidate_final_attestation_v76_10.json"
    summary_path = output_dir / "release_candidate_final_attestation_summary_v76_10.json"
    report_path = output_dir / "release_candidate_final_attestation_v76_10.txt"

    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    summary = {
        "schema_version": result["schema_version"],
        "version": result["version"],
        "attestation_type": result["attestation_type"],
        "status": result["status"],
        "decision": result["decision"],
        "issued_at_utc": result["issued_at_utc"],
        "framework_commit_sha": result["repository"]["framework_commit_sha"],
        "attested_chain": result["attested_chain"],
        "anchored_hashes": result["anchored_hashes"],
        "final_attestation_sha256": result["final_attestation_sha256"],
        "gate_count": result["attestation_result"]["gate_count"],
        "passed_gate_count": result["attestation_result"]["passed_gate_count"],
        "failed_gate_count": result["attestation_result"]["failed_gate_count"],
        "failed_gate_ids": result["attestation_result"]["failed_gate_ids"],
        "release_candidate_finally_attested":
            result["release_candidate_finally_attested"],
        "network_allowed": result["network_allowed"],
        "orders_submitted": result["orders_submitted"],
        "approved_for_live": result["approved_for_live"],
        "live_trading_authorized": result["live_trading_authorized"],
        "next_phase": result["next_phase"],
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
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
        result = issue_attestation(Path(args.repository_root), config)
        outputs = write_outputs(Path(args.output_dir), result)
    except (AttestationError, OSError, ValueError) as exc:
        print(json.dumps({
            "status": "ERROR",
            "error": str(exc),
            "approved_for_live": False,
            "live_trading_authorized": False,
        }, indent=2, sort_keys=True))
        return 2

    print(json.dumps({
        "status": result["status"],
        "decision": result["decision"],
        "release_candidate_finally_attested":
            result["release_candidate_finally_attested"],
        "gate_count": result["attestation_result"]["gate_count"],
        "passed_gate_count": result["attestation_result"]["passed_gate_count"],
        "failed_gate_count": result["attestation_result"]["failed_gate_count"],
        "failed_gate_ids": result["attestation_result"]["failed_gate_ids"],
        "final_attestation_sha256": result["final_attestation_sha256"],
        "network_allowed": result["network_allowed"],
        "orders_submitted": result["orders_submitted"],
        "approved_for_live": result["approved_for_live"],
        "live_trading_authorized": result["live_trading_authorized"],
        "next_phase": result["next_phase"],
        "outputs": [str(p) for p in outputs],
    }, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
