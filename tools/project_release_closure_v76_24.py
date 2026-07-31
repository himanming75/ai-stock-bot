from __future__ import annotations
import argparse, hashlib, json, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "76.24"
SCHEMA = "v76.24.project_release_closure.1"
NEXT_PHASE = "V77_BROKER_SANDBOX_INTEGRATION"

class ProjectReleaseClosureError(ValueError):
    pass

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ProjectReleaseClosureError(f"required JSON not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ProjectReleaseClosureError(f"invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ProjectReleaseClosureError(f"JSON root must be object: {path}")
    return value

def validate_hex(value: Any, length: int, name: str) -> None:
    if not isinstance(value, str) or len(value) != length:
        raise ProjectReleaseClosureError(f"{name} must be {length} hexadecimal characters")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ProjectReleaseClosureError(f"{name} must be hexadecimal") from exc

def validate_config(config: dict[str, Any]) -> None:
    if config.get("closure_scope") != "PROJECT_RELEASE_CLOSURE":
        raise ProjectReleaseClosureError("closure_scope invalid")
    for key in (
        "offline_only","require_git_tracked_clean","require_head_matches_origin_main",
        "require_verification_self_hash","require_verification_chain_self_hash",
        "require_fixed_anchor_match","require_v76_23_zero_failed_gates",
        "require_zero_trading_side_effects",
    ):
        if config.get(key) is not True:
            raise ProjectReleaseClosureError(f"{key} must be true")
    for key in (
        "network_allowed","broker_connection_allowed","order_submission_allowed",
        "live_trading_allowed","live_approval_allowed",
    ):
        if config.get(key) is not False:
            raise ProjectReleaseClosureError(f"{key} must be false")
    validate_hex(config.get("expected_framework_commit_sha"), 7, "expected_framework_commit_sha")
    validate_hex(config.get("expected_verification_sha256"), 64, "expected_verification_sha256")
    validate_hex(config.get("expected_verification_chain_sha256"), 64, "expected_verification_chain_sha256")

def run_git(root: Path, args: list[str]) -> str:
    p = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", check=False)
    if p.returncode != 0:
        raise ProjectReleaseClosureError(f"git {' '.join(args)} failed: {p.stderr.strip()}")
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

def create_closure(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    validate_config(config)
    started = time.time()
    git = git_state(root)
    gates: list[dict[str, Any]] = []

    add_gate(gates, "GIT_HEAD_MATCHES_ORIGIN_MAIN", git["head_sha"] == git["origin_main_sha"])
    add_gate(gates, "GIT_HEAD_MATCHES_FRAMEWORK_COMMIT", git["head_short_sha"] == config["expected_framework_commit_sha"])
    add_gate(gates, "GIT_BRANCH_MAIN", git["branch"] == "main")
    add_gate(gates, "GIT_TRACKED_WORKING_TREE_CLEAN", git["tracked_status_short"] == [])

    source_path = root / "release/v76_23/output/release_archive_completion_certificate_verification_v76_23.json"
    add_gate(gates, "V76_23_VERIFICATION_EXISTS", source_path.is_file())
    source = load_json(source_path)

    stored_verification = source.get("verification_sha256")
    calculated_verification = digest({
        k:v for k,v in source.items()
        if k not in {"verification_sha256","issued_at_utc","duration_seconds"}
    })
    add_gate(gates, "V76_23_VERIFICATION_SELF_HASH", stored_verification == calculated_verification)
    add_gate(gates, "V76_23_VERIFICATION_FIXED_ANCHOR", stored_verification == config["expected_verification_sha256"])

    chain = source.get("verification_chain")
    calculated_chain = digest(chain) if isinstance(chain, dict) else None
    add_gate(gates, "V76_23_VERIFICATION_CHAIN_OBJECT", isinstance(chain, dict))
    add_gate(gates, "V76_23_VERIFICATION_CHAIN_SELF_HASH", source.get("verification_chain_sha256") == calculated_chain)
    add_gate(gates, "V76_23_VERIFICATION_CHAIN_FIXED_ANCHOR",
             source.get("verification_chain_sha256") == config["expected_verification_chain_sha256"])

    vr = source.get("verification_result", {})
    required = {
        "V76_23_STATUS_PASS": source.get("status") == "PASS",
        "V76_23_DECISION_VERIFIED":
            source.get("decision") == "release_archive_completion_certificate_independently_verified",
        "V76_23_TYPE_MATCH":
            source.get("verification_type") == "RELEASE_ARCHIVE_COMPLETION_CERTIFICATE_VERIFICATION",
        "V76_23_CERTIFICATE_VERIFIED":
            source.get("release_archive_completion_certificate_independently_verified") is True,
        "V76_23_COMPLETION_CERTIFIED":
            source.get("release_archive_completion_certified") is True,
        "V76_23_FINALIZATION_VERIFIED":
            source.get("release_archive_finalization_independently_verified") is True,
        "V76_23_ARCHIVE_FINALIZED": source.get("release_archive_finalized") is True,
        "V76_23_CLOSURE_VERIFIED":
            source.get("release_archive_closure_independently_verified") is True,
        "V76_23_CLOSURE_CERTIFIED":
            source.get("release_archive_closure_certified") is True,
        "V76_23_ARCHIVE_SEALED": source.get("release_archive_sealed") is True,
        "V76_23_CANDIDATE_CLOSED": source.get("release_candidate_closed") is True,
        "V76_23_ZERO_FAILED_GATES": vr.get("failed_gate_count") == 0,
        "V76_23_FAILED_GATE_IDS_EMPTY": vr.get("failed_gate_ids") == [],
        "V76_23_NETWORK_DISABLED": source.get("network_allowed") is False,
        "V76_23_BROKER_NOT_CONNECTED": source.get("broker_connected") is False,
        "V76_23_ZERO_ORDERS": source.get("orders_submitted") == 0,
        "V76_23_NOT_APPROVED_FOR_LIVE": source.get("approved_for_live") is False,
        "V76_23_LIVE_TRADING_NOT_AUTHORIZED": source.get("live_trading_authorized") is False,
        "V76_23_NEXT_PHASE_MATCH": source.get("next_phase") == "V76_24_PROJECT_RELEASE_CLOSURE",
    }
    for gid, passed in required.items():
        add_gate(gates, gid, passed)

    failed = [g["gate_id"] for g in gates if g["status"] != "PASS"]
    status = "PASS" if not failed else "FAIL"
    anchors = {
        "v76_23_verification_sha256": stored_verification,
        "v76_23_verification_chain_sha256": source.get("verification_chain_sha256"),
    }
    closure_chain = {
        **anchors,
        "v76_23_framework_commit_sha": source.get("repository",{}).get("framework_commit_sha"),
        "v76_23_schema_version": source.get("schema_version"),
        "v76_23_verification_type": source.get("verification_type"),
        "v76_23_decision": source.get("decision"),
    }
    result = {
        "schema_version": SCHEMA,
        "version": VERSION,
        "record_type": "PROJECT_RELEASE_CLOSURE",
        "issued_at_utc": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(time.time()-started,6),
        "status": status,
        "decision": (
            "offline_paper_project_release_closed"
            if status == "PASS" else "project_release_closure_failed"
        ),
        "repository": {
            "framework_commit_sha": git["head_sha"],
            "origin_main_sha": git["origin_main_sha"],
            "branch": git["branch"],
            "tracked_working_tree_clean": git["tracked_status_short"] == [],
        },
        "closure_anchors": anchors,
        "closure_chain": closure_chain,
        "closure_chain_sha256": digest(closure_chain),
        "closure_result": {
            "gate_count": len(gates),
            "passed_gate_count": len(gates)-len(failed),
            "failed_gate_count": len(failed),
            "failed_gate_ids": failed,
            "gates": gates,
        },
        "offline_paper_release_complete": status == "PASS",
        "project_release_closed": status == "PASS",
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
        "live_trading_ready": False,
        "next_phase": NEXT_PHASE if status == "PASS" else "REPAIR_V76_24_PROJECT_RELEASE_CLOSURE",
    }
    immutable = {k:v for k,v in result.items() if k not in {"closure_sha256","issued_at_utc","duration_seconds"}}
    result["closure_sha256"] = digest(immutable)
    return result

def summary_from(result: dict[str, Any]) -> dict[str, Any]:
    cr = result["closure_result"]
    return {
        "status": result["status"],
        "decision": result["decision"],
        "framework_commit_sha": result["repository"]["framework_commit_sha"],
        "closure_sha256": result["closure_sha256"],
        "closure_chain_sha256": result["closure_chain_sha256"],
        **result["closure_anchors"],
        "gate_count": cr["gate_count"],
        "passed_gate_count": cr["passed_gate_count"],
        "failed_gate_count": cr["failed_gate_count"],
        "failed_gate_ids": cr["failed_gate_ids"],
        "offline_paper_release_complete": result["offline_paper_release_complete"],
        "project_release_closed": result["project_release_closed"],
        "network_allowed": result["network_allowed"],
        "orders_submitted": result["orders_submitted"],
        "approved_for_live": result["approved_for_live"],
        "live_trading_authorized": result["live_trading_authorized"],
        "live_trading_ready": result["live_trading_ready"],
        "next_phase": result["next_phase"],
    }

def write_outputs(result: dict[str, Any], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    p1 = output_dir/"project_release_closure_v76_24.json"
    p2 = output_dir/"project_release_closure_summary_v76_24.json"
    p3 = output_dir/"project_release_closure_v76_24.txt"
    p1.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    p2.write_text(json.dumps(summary_from(result), indent=2, sort_keys=True)+"\n", encoding="utf-8")
    p3.write_text("V76.24 PROJECT RELEASE CLOSURE\n" +
                  "\n".join(f"{k}: {v}" for k,v in summary_from(result).items())+"\n", encoding="utf-8")
    return [p1,p2,p3]

def cli() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repository-root", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--output-dir", required=True)
    a = p.parse_args()
    result = create_closure(Path(a.repository_root), load_json(Path(a.config)))
    write_outputs(result, Path(a.output_dir))
    print(json.dumps(summary_from(result), indent=2))
    return 0 if result["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(cli())
