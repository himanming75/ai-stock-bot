from __future__ import annotations
import argparse, hashlib, json, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "76.23"
SCHEMA = "v76.23.release_archive_completion_certificate_verification.1"
NEXT_PHASE = "V76_24_PROJECT_RELEASE_CLOSURE"

class CompletionCertificateVerificationError(ValueError):
    pass

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CompletionCertificateVerificationError(f"required JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CompletionCertificateVerificationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise CompletionCertificateVerificationError(f"JSON root must be object: {path}")
    return value

def validate_hex(value: Any, length: int, name: str) -> None:
    if not isinstance(value, str) or len(value) != length:
        raise CompletionCertificateVerificationError(f"{name} must be {length} hexadecimal characters")
    try:
        int(value, 16)
    except ValueError as exc:
        raise CompletionCertificateVerificationError(f"{name} must be hexadecimal") from exc

def validate_config(config: dict[str, Any]) -> None:
    if config.get("verification_scope") != "RELEASE_ARCHIVE_COMPLETION_CERTIFICATE_VERIFICATION":
        raise CompletionCertificateVerificationError("verification_scope invalid")
    for key in (
        "offline_only","independent_verification_required","require_git_tracked_clean",
        "require_head_matches_origin_main","require_certificate_self_hash",
        "require_completion_chain_self_hash","require_fixed_anchor_match",
        "require_v76_22_zero_failed_gates","require_zero_trading_side_effects",
    ):
        if config.get(key) is not True:
            raise CompletionCertificateVerificationError(f"{key} must be true")
    for key in (
        "network_allowed","broker_connection_allowed","order_submission_allowed",
        "live_trading_allowed","live_approval_allowed",
    ):
        if config.get(key) is not False:
            raise CompletionCertificateVerificationError(f"{key} must be false")
    validate_hex(config.get("expected_framework_commit_sha"), 7, "expected_framework_commit_sha")
    validate_hex(config.get("expected_certificate_sha256"), 64, "expected_certificate_sha256")
    validate_hex(config.get("expected_completion_chain_sha256"), 64, "expected_completion_chain_sha256")

def run_git(root: Path, args: list[str]) -> str:
    p = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", check=False)
    if p.returncode != 0:
        raise CompletionCertificateVerificationError(
            f"git {' '.join(args)} failed: {p.stderr.strip()}"
        )
    return p.stdout.strip()

def git_state(root: Path) -> dict[str, Any]:
    tracked = run_git(root, ["status","--short","--untracked-files=no"])
    return {
        "head_sha": run_git(root, ["rev-parse","HEAD"]),
        "head_short_sha": run_git(root, ["rev-parse","--short=7","HEAD"]),
        "origin_main_sha": run_git(root, ["rev-parse","origin/main"]),
        "branch": run_git(root, ["rev-parse","--abbrev-ref","HEAD"]),
        "tracked_status_short": tracked.splitlines() if tracked else [],
    }

def add_gate(gates: list[dict[str, Any]], gate_id: str, passed: bool) -> None:
    gates.append({"gate_id":gate_id, "status":"PASS" if passed else "FAIL"})

def create_verification(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    validate_config(config)
    started = time.time()
    git = git_state(root)
    gates: list[dict[str, Any]] = []

    add_gate(gates, "GIT_HEAD_MATCHES_ORIGIN_MAIN", git["head_sha"] == git["origin_main_sha"])
    add_gate(gates, "GIT_HEAD_MATCHES_FRAMEWORK_COMMIT", git["head_short_sha"] == config["expected_framework_commit_sha"])
    add_gate(gates, "GIT_BRANCH_MAIN", git["branch"] == "main")
    add_gate(gates, "GIT_TRACKED_WORKING_TREE_CLEAN", git["tracked_status_short"] == [])

    source_path = root / "release/v76_22/output/release_archive_completion_certificate_v76_22.json"
    add_gate(gates, "V76_22_CERTIFICATE_EXISTS", source_path.is_file())
    source = load_json(source_path)

    stored_cert = source.get("certificate_sha256")
    calculated_cert = digest({
        k:v for k,v in source.items()
        if k not in {"certificate_sha256","issued_at_utc","duration_seconds"}
    })
    add_gate(gates, "V76_22_CERTIFICATE_SELF_HASH", stored_cert == calculated_cert)
    add_gate(gates, "V76_22_CERTIFICATE_FIXED_ANCHOR", stored_cert == config["expected_certificate_sha256"])

    chain = source.get("completion_chain")
    calculated_chain = digest(chain) if isinstance(chain, dict) else None
    add_gate(gates, "V76_22_COMPLETION_CHAIN_OBJECT", isinstance(chain, dict))
    add_gate(gates, "V76_22_COMPLETION_CHAIN_SELF_HASH", source.get("completion_chain_sha256") == calculated_chain)
    add_gate(gates, "V76_22_COMPLETION_CHAIN_FIXED_ANCHOR",
             source.get("completion_chain_sha256") == config["expected_completion_chain_sha256"])

    cr = source.get("certificate_result", {})
    required = {
        "V76_22_STATUS_PASS": source.get("status") == "PASS",
        "V76_22_DECISION_CERTIFIED": source.get("decision") == "release_archive_completion_certified",
        "V76_22_RECORD_TYPE_MATCH": source.get("record_type") == "RELEASE_ARCHIVE_COMPLETION_CERTIFICATE",
        "V76_22_COMPLETION_CERTIFIED": source.get("release_archive_completion_certified") is True,
        "V76_22_FINALIZATION_VERIFIED": source.get("release_archive_finalization_independently_verified") is True,
        "V76_22_ARCHIVE_FINALIZED": source.get("release_archive_finalized") is True,
        "V76_22_CLOSURE_VERIFIED": source.get("release_archive_closure_independently_verified") is True,
        "V76_22_CLOSURE_CERTIFIED": source.get("release_archive_closure_certified") is True,
        "V76_22_ARCHIVE_SEALED": source.get("release_archive_sealed") is True,
        "V76_22_CANDIDATE_CLOSED": source.get("release_candidate_closed") is True,
        "V76_22_ZERO_FAILED_GATES": cr.get("failed_gate_count") == 0,
        "V76_22_FAILED_GATE_IDS_EMPTY": cr.get("failed_gate_ids") == [],
        "V76_22_NETWORK_DISABLED": source.get("network_allowed") is False,
        "V76_22_BROKER_NOT_CONNECTED": source.get("broker_connected") is False,
        "V76_22_ZERO_ORDERS": source.get("orders_submitted") == 0,
        "V76_22_NOT_APPROVED_FOR_LIVE": source.get("approved_for_live") is False,
        "V76_22_LIVE_TRADING_NOT_AUTHORIZED": source.get("live_trading_authorized") is False,
        "V76_22_NEXT_PHASE_MATCH": source.get("next_phase") == "V76_23_RELEASE_ARCHIVE_COMPLETION_CERTIFICATE_VERIFICATION",
    }
    for gid, passed in required.items():
        add_gate(gates, gid, passed)

    failed = [g["gate_id"] for g in gates if g["status"] != "PASS"]
    status = "PASS" if not failed else "FAIL"
    anchors = {
        "v76_22_certificate_sha256": stored_cert,
        "v76_22_completion_chain_sha256": source.get("completion_chain_sha256"),
    }
    verification_chain = {
        **anchors,
        "v76_22_framework_commit_sha": source.get("repository",{}).get("framework_commit_sha"),
        "v76_22_schema_version": source.get("schema_version"),
        "v76_22_record_type": source.get("record_type"),
        "v76_22_decision": source.get("decision"),
    }
    result = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "verification_type": "RELEASE_ARCHIVE_COMPLETION_CERTIFICATE_VERIFICATION",
        "issued_at_utc": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(time.time()-started,6),
        "status": status,
        "decision": (
            "release_archive_completion_certificate_independently_verified"
            if status == "PASS" else "release_archive_completion_certificate_verification_failed"
        ),
        "repository": {
            "framework_commit_sha": git["head_sha"],
            "origin_main_sha": git["origin_main_sha"],
            "branch": git["branch"],
            "tracked_working_tree_clean": git["tracked_status_short"] == [],
        },
        "verified_anchors": anchors,
        "verification_chain": verification_chain,
        "verification_chain_sha256": digest(verification_chain),
        "verification_result": {
            "gate_count": len(gates),
            "passed_gate_count": len(gates)-len(failed),
            "failed_gate_count": len(failed),
            "failed_gate_ids": failed,
            "gates": gates,
        },
        "release_archive_completion_certificate_independently_verified": status == "PASS",
        "release_archive_completion_certified": status == "PASS",
        "release_archive_finalization_independently_verified": status == "PASS",
        "release_archive_finalized": status == "PASS",
        "release_archive_closure_independently_verified": status == "PASS",
        "release_archive_closure_certified": status == "PASS",
        "release_archive_sealed": status == "PASS",
        "release_candidate_closed": status == "PASS",
        "network_allowed": False,
        "broker_connected": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "next_phase": NEXT_PHASE if status == "PASS" else "REPAIR_V76_23_COMPLETION_CERTIFICATE_VERIFICATION",
    }
    immutable = {k:v for k,v in result.items() if k not in {"verification_sha256","issued_at_utc","duration_seconds"}}
    result["verification_sha256"] = digest(immutable)
    return result

def summary_from(result: dict[str, Any]) -> dict[str, Any]:
    vr = result["verification_result"]
    return {
        "status": result["status"],
        "decision": result["decision"],
        "framework_commit_sha": result["repository"]["framework_commit_sha"],
        "verification_sha256": result["verification_sha256"],
        "verification_chain_sha256": result["verification_chain_sha256"],
        **result["verified_anchors"],
        "gate_count": vr["gate_count"],
        "passed_gate_count": vr["passed_gate_count"],
        "failed_gate_count": vr["failed_gate_count"],
        "failed_gate_ids": vr["failed_gate_ids"],
        "release_archive_completion_certificate_independently_verified":
            result["release_archive_completion_certificate_independently_verified"],
        "network_allowed": result["network_allowed"],
        "orders_submitted": result["orders_submitted"],
        "approved_for_live": result["approved_for_live"],
        "live_trading_authorized": result["live_trading_authorized"],
        "next_phase": result["next_phase"],
    }

def write_outputs(result: dict[str, Any], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    p1 = output_dir/"release_archive_completion_certificate_verification_v76_23.json"
    p2 = output_dir/"release_archive_completion_certificate_verification_summary_v76_23.json"
    p3 = output_dir/"release_archive_completion_certificate_verification_v76_23.txt"
    p1.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    p2.write_text(json.dumps(summary_from(result), indent=2, sort_keys=True)+"\n", encoding="utf-8")
    p3.write_text("V76.23 RELEASE ARCHIVE COMPLETION CERTIFICATE VERIFICATION\n" +
                  "\n".join(f"{k}: {v}" for k,v in summary_from(result).items())+"\n", encoding="utf-8")
    return [p1,p2,p3]

def cli() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--output-dir", required=True)
    a = p.parse_args()
    result = create_verification(Path(a.repository_root), load_json(Path(a.config)))
    write_outputs(result, Path(a.output_dir))
    print(json.dumps(summary_from(result), indent=2))
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(cli())
