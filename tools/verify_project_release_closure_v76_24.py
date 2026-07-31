from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from tools.project_release_closure_v76_24 import digest, load_json, summary_from

EXPECTED_NEXT = "V77_BROKER_SANDBOX_INTEGRATION"

def verify_output(output_dir: Path) -> dict[str, Any]:
    result = load_json(output_dir/"project_release_closure_v76_24.json")
    summary = load_json(output_dir/"project_release_closure_summary_v76_24.json")
    text_path = output_dir/"project_release_closure_v76_24.txt"
    errors: list[str] = []

    stored = result.get("closure_sha256")
    calculated = digest({
        k:v for k,v in result.items()
        if k not in {"closure_sha256","issued_at_utc","duration_seconds"}
    })
    if stored != calculated:
        errors.append("closure self-hash mismatch")

    chain = result.get("closure_chain")
    if not isinstance(chain, dict):
        errors.append("closure chain must be an object")
    elif result.get("closure_chain_sha256") != digest(chain):
        errors.append("closure chain hash mismatch")

    if summary != summary_from(result):
        errors.append("summary mismatch")
    if not text_path.is_file():
        errors.append("text output missing")

    cr = result.get("closure_result", {})
    gates = cr.get("gates")
    checks = [
        (result.get("status") == "PASS", "status is not PASS"),
        (result.get("decision") == "offline_paper_project_release_closed", "decision mismatch"),
        (result.get("record_type") == "PROJECT_RELEASE_CLOSURE", "record type mismatch"),
        (result.get("offline_paper_release_complete") is True, "offline release completion mismatch"),
        (result.get("project_release_closed") is True, "project closure mismatch"),
        (cr.get("failed_gate_count") == 0, "failed gate count must be zero"),
        (cr.get("failed_gate_ids") == [], "failed gate IDs must be empty"),
        (result.get("network_allowed") is False, "network_allowed mismatch"),
        (result.get("broker_connected") is False, "broker_connected mismatch"),
        (result.get("orders_submitted") == 0, "orders_submitted mismatch"),
        (result.get("approved_for_live") is False, "approved_for_live mismatch"),
        (result.get("live_trading_authorized") is False, "live_trading_authorized mismatch"),
        (result.get("live_trading_ready") is False, "live_trading_ready mismatch"),
        (result.get("next_phase") == EXPECTED_NEXT, "next_phase mismatch"),
    ]
    for ok, msg in checks:
        if not ok:
            errors.append(msg)

    if not isinstance(gates, list):
        errors.append("gates must be a list")
    else:
        if cr.get("gate_count") != len(gates):
            errors.append("gate count mismatch")
        if cr.get("passed_gate_count") != len(gates):
            errors.append("passed gate count mismatch")
        if any(g.get("status") != "PASS" for g in gates):
            errors.append("not all gates passed")

    verified = not errors
    return {
        "verified": verified,
        "status": "PASS" if verified else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        "closure_sha256": stored,
        "closure_chain_sha256": result.get("closure_chain_sha256"),
        "offline_paper_release_complete": result.get("offline_paper_release_complete"),
        "project_release_closed": result.get("project_release_closed"),
        "next_phase": result.get("next_phase"),
    }

def cli() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output-dir", required=True)
    a = p.parse_args()
    checked = verify_output(Path(a.output_dir))
    print(json.dumps(checked, indent=2))
    return 0 if checked["verified"] else 1

if __name__ == "__main__":
    raise SystemExit(cli())
