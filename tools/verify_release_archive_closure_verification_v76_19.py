from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Any
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.release_archive_closure_verification_v76_19 import digest, load_json, summary_from
EXPECTED_NEXT = "V76_20_RELEASE_ARCHIVE_FINALIZATION"

def verify_output(output_dir: Path) -> dict[str, Any]:
    result = load_json(output_dir / "release_archive_closure_verification_v76_19.json")
    summary = load_json(output_dir / "release_archive_closure_verification_summary_v76_19.json")
    errors: list[str] = []
    stored = result.get("verification_sha256")
    calculated = digest({k: v for k, v in result.items() if k not in {"verification_sha256", "issued_at_utc", "duration_seconds"}})
    if stored != calculated: errors.append("verification self-hash mismatch")
    chain = result.get("verification_chain", {})
    if result.get("verification_chain_sha256") != digest(chain): errors.append("verification chain hash mismatch")
    if summary != summary_from(result): errors.append("summary mismatch")
    if not (output_dir / "release_archive_closure_verification_v76_19.txt").is_file(): errors.append("text output missing")
    check = result.get("verification_result", {})
    expected = {
        "status": "PASS", "decision": "release_archive_closure_independently_verified",
        "release_archive_closure_independently_verified": True,
        "release_archive_closure_certified": True, "release_archive_sealed": True,
        "release_candidate_closed": True, "network_allowed": False,
        "broker_connected": False, "orders_submitted": 0,
        "approved_for_live": False, "live_trading_authorized": False,
        "next_phase": EXPECTED_NEXT,
    }
    for key, value in expected.items():
        if result.get(key) != value: errors.append(f"{key} mismatch")
    gates = check.get("gates")
    if check.get("failed_gate_count") != 0: errors.append("failed gate count must be zero")
    if check.get("failed_gate_ids") != []: errors.append("failed gate IDs must be empty")
    if not isinstance(gates, list): errors.append("gates must be a list")
    elif check.get("gate_count") != len(gates) or check.get("passed_gate_count") != len(gates) or any(g.get("status") != "PASS" for g in gates):
        errors.append("gate accounting mismatch")
    verified = not errors
    return {"verified": verified, "status": "PASS" if verified else "FAIL", "error_count": len(errors), "errors": errors,
            "verification_sha256": stored, "verification_chain_sha256": result.get("verification_chain_sha256"),
            **result.get("verified_anchors", {}), "next_phase": result.get("next_phase")}

def cli() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--output-dir", required=True); args = parser.parse_args()
    checked = verify_output(Path(args.output_dir)); print(json.dumps(checked, indent=2)); return 0 if checked["verified"] else 1
if __name__ == "__main__": raise SystemExit(cli())
