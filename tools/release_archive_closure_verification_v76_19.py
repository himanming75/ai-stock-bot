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

VERSION = "76.19"
SCHEMA = "v76.19.release_archive_closure_verification.1"
NEXT_PHASE = "V76_20_RELEASE_ARCHIVE_FINALIZATION"

class ClosureVerificationError(ValueError):
    pass

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ClosureVerificationError(f"required JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ClosureVerificationError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ClosureVerificationError(f"JSON root must be object: {path}")
    return value

def validate_hex(value: Any, length: int, name: str) -> None:
    if not isinstance(value, str) or len(value) != length:
        raise ClosureVerificationError(f"{name} must be {length} hexadecimal characters")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ClosureVerificationError(f"{name} must be hexadecimal") from exc

def validate_config(config: dict[str, Any]) -> None:
    if config.get("verification_scope") != "RELEASE_ARCHIVE_CLOSURE_VERIFICATION":
        raise ClosureVerificationError("verification_scope invalid")
    for key in (
        "offline_only", "independent_verification_required",
        "require_git_tracked_clean", "require_head_matches_origin_main",
        "require_framework_commit_match", "require_certificate_self_hash",
        "require_closure_chain_self_hash", "require_fixed_anchor_match",
        "require_zero_failed_gates", "require_zero_trading_side_effects",
    ):
        if config.get(key) is not True:
            raise ClosureVerificationError(f"{key} must be true")
    for key in (
        "network_allowed", "broker_connection_allowed",
        "order_submission_allowed", "live_trading_allowed",
        "live_approval_allowed",
    ):
        if config.get(key) is not False:
            raise ClosureVerificationError(f"{key} must be false")
    validate_hex(config.get("expected_framework_commit_sha"), 40, "expected_framework_commit_sha")
    validate_hex(config.get("expected_closure_certificate_sha256"), 64, "expected_closure_certificate_sha256")
    validate_hex(config.get("expected_closure_chain_sha256"), 64, "expected_closure_chain_sha256")

def run_git(root: Path, args: list[str]) -> str:
    completed = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", check=False)
    if completed.returncode != 0:
        raise ClosureVerificationError(f"git {' '.join(args)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()

def git_state(root: Path) -> dict[str, Any]:
    tracked = run_git(root, ["status", "--short", "--untracked-files=no"])
    return {
        "head_sha": run_git(root, ["rev-parse", "HEAD"]),
        "origin_main_sha": run_git(root, ["rev-parse", "origin/main"]),
        "branch": run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"]),
        "tracked_status_short": tracked.splitlines() if tracked else [],
    }

def add_gate(gates: list[dict[str, Any]], gate_id: str, passed: bool, **details: Any) -> None:
    gate = {"gate_id": gate_id, "status": "PASS" if passed else "FAIL"}
    gate.update(details)
    gates.append(gate)

def create_closure_verification(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    validate_config(config)
    started = time.time()
    git = git_state(root)
    gates: list[dict[str, Any]] = []

    add_gate(gates, "GIT_HEAD_MATCHES_ORIGIN_MAIN", git["head_sha"] == git["origin_main_sha"])
    add_gate(gates, "GIT_HEAD_MATCHES_FRAMEWORK_COMMIT", git["head_sha"] == config["expected_framework_commit_sha"])
    add_gate(gates, "GIT_BRANCH_MAIN", git["branch"] == "main")
    add_gate(gates, "GIT_TRACKED_WORKING_TREE_CLEAN", git["tracked_status_short"] == [])

    source_path = root / "release/v76_18/output/release_archive_closure_certificate_v76_18.json"
    add_gate(gates, "V76_18_CERTIFICATE_EXISTS", source_path.is_file())
    source = load_json(source_path)

    stored_certificate = source.get("closure_certificate_sha256")
    calculated_certificate = digest({
        key: value for key, value in source.items()
        if key not in {"closure_certificate_sha256", "issued_at_utc", "duration_seconds"}
    })
    add_gate(gates, "V76_18_CERTIFICATE_SELF_HASH", stored_certificate == calculated_certificate)
    add_gate(gates, "V76_18_CERTIFICATE_FIXED_ANCHOR", stored_certificate == config["expected_closure_certificate_sha256"])

    closure_chain = source.get("closure_chain")
    calculated_chain = digest(closure_chain) if isinstance(closure_chain, dict) else None
    add_gate(gates, "V76_18_CLOSURE_CHAIN_OBJECT", isinstance(closure_chain, dict))
    add_gate(gates, "V76_18_CLOSURE_CHAIN_SELF_HASH", source.get("closure_chain_sha256") == calculated_chain)
    add_gate(gates, "V76_18_CLOSURE_CHAIN_FIXED_ANCHOR", source.get("closure_chain_sha256") == config["expected_closure_chain_sha256"])

    cert_result = source.get("certificate_result", {})
    required = {
        "V76_18_STATUS_PASS": source.get("status") == "PASS",
        "V76_18_DECISION_CERTIFIED": source.get("decision") == "release_archive_closure_certified",
        "V76_18_CLOSURE_CERTIFIED": source.get("release_archive_closure_certified") is True,
        "V76_18_INDEPENDENTLY_VERIFIED": source.get("release_archive_independently_verified") is True,
        "V76_18_ARCHIVE_SEALED": source.get("release_archive_sealed") is True,
        "V76_18_CANDIDATE_CLOSED": source.get("release_candidate_closed") is True,
        "V76_18_ZERO_FAILED_GATES": cert_result.get("failed_gate_count") == 0,
        "V76_18_FAILED_GATE_IDS_EMPTY": cert_result.get("failed_gate_ids") == [],
        "V76_18_NETWORK_DISABLED": source.get("network_allowed") is False,
        "V76_18_BROKER_NOT_CONNECTED": source.get("broker_connected") is False,
        "V76_18_ZERO_ORDERS": source.get("orders_submitted") == 0,
        "V76_18_NOT_APPROVED_FOR_LIVE": source.get("approved_for_live") is False,
        "V76_18_LIVE_TRADING_NOT_AUTHORIZED": source.get("live_trading_authorized") is False,
        "V76_18_NEXT_PHASE_MATCH": source.get("next_phase") == "V76_19_RELEASE_ARCHIVE_CLOSURE_VERIFICATION",
    }
    for gate_id, passed in required.items():
        add_gate(gates, gate_id, passed)

    failed = [gate["gate_id"] for gate in gates if gate["status"] != "PASS"]
    status = "PASS" if not failed else "FAIL"
    verified_anchors = {
        "v76_18_closure_certificate_sha256": stored_certificate,
        "v76_18_closure_chain_sha256": source.get("closure_chain_sha256"),
    }
    verification_chain = {
        **verified_anchors,
        "v76_18_framework_commit_sha": source.get("repository", {}).get("framework_commit_sha"),
        "v76_18_certificate_schema": source.get("schema_version"),
    }
    result = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "verification_type": "RELEASE_ARCHIVE_CLOSURE_VERIFICATION",
        "issued_at_utc": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(time.time() - started, 6),
        "status": status,
        "decision": "release_archive_closure_independently_verified" if status == "PASS" else "release_archive_closure_verification_failed",
        "repository": {
            "framework_commit_sha": git["head_sha"],
            "origin_main_sha": git["origin_main_sha"],
            "branch": git["branch"],
            "tracked_working_tree_clean": git["tracked_status_short"] == [],
        },
        "verified_anchors": verified_anchors,
        "verification_chain": verification_chain,
        "verification_chain_sha256": digest(verification_chain),
        "verification_result": {
            "gate_count": len(gates),
            "passed_gate_count": len(gates) - len(failed),
            "failed_gate_count": len(failed),
            "failed_gate_ids": failed,
            "gates": gates,
        },
        "release_archive_closure_independently_verified": status == "PASS",
        "release_archive_closure_certified": status == "PASS",
        "release_archive_sealed": status == "PASS",
        "release_candidate_closed": status == "PASS",
        "network_allowed": False,
        "broker_connected": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "next_phase": NEXT_PHASE if status == "PASS" else "REPAIR_V76_19_CLOSURE_VERIFICATION",
    }
    immutable = {k: v for k, v in result.items() if k not in {"issued_at_utc", "duration_seconds"}}
    result["verification_sha256"] = digest(immutable)
    return result

def summary_from(result: dict[str, Any]) -> dict[str, Any]:
    check = result["verification_result"]
    return {
        "status": result["status"], "decision": result["decision"],
        "framework_commit_sha": result["repository"]["framework_commit_sha"],
        "verification_sha256": result["verification_sha256"],
        "verification_chain_sha256": result["verification_chain_sha256"],
        **result["verified_anchors"],
        "gate_count": check["gate_count"], "passed_gate_count": check["passed_gate_count"],
        "failed_gate_count": check["failed_gate_count"], "failed_gate_ids": check["failed_gate_ids"],
        "release_archive_closure_independently_verified": result["release_archive_closure_independently_verified"],
        "release_archive_closure_certified": result["release_archive_closure_certified"],
        "release_archive_sealed": result["release_archive_sealed"],
        "release_candidate_closed": result["release_candidate_closed"],
        "network_allowed": result["network_allowed"], "orders_submitted": result["orders_submitted"],
        "approved_for_live": result["approved_for_live"], "live_trading_authorized": result["live_trading_authorized"],
        "next_phase": result["next_phase"],
    }

def write_outputs(result: dict[str, Any], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = [
        output_dir / "release_archive_closure_verification_v76_19.json",
        output_dir / "release_archive_closure_verification_summary_v76_19.json",
        output_dir / "release_archive_closure_verification_v76_19.txt",
    ]
    paths[0].write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths[1].write_text(json.dumps(summary_from(result), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths[2].write_text("V76.19 RELEASE ARCHIVE CLOSURE VERIFICATION\n" + "\n".join(f"{k}: {v}" for k, v in summary_from(result).items()) + "\n", encoding="utf-8")
    return paths

def cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    try:
        result = create_closure_verification(Path(args.repository_root), load_json(Path(args.config)))
        write_outputs(result, Path(args.output_dir))
        print(json.dumps(summary_from(result), indent=2))
        return 0 if result["status"] == "PASS" else 1
    except ClosureVerificationError as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, indent=2))
        return 2

if __name__ == "__main__":
    raise SystemExit(cli())
