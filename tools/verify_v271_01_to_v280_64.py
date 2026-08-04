import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from multi_timeframe_strategy.engine import evaluate

r = evaluate(ROOT)
checks = {
    "stage": r["stage"] == "V280.64",
    "status": r["status"] == "PASS",
    "allowed_state": r["state"] in {
        "MULTI_TIMEFRAME_STRATEGY_ENSEMBLE_READY",
        "MULTI_TIMEFRAME_STRATEGY_ENSEMBLE_REVIEW_REQUIRED",
    },
    "strategies_present": bool(r["strategy_rows"]),
    "allocation_present": bool(r["allocation"]),
    "candidate_present": bool(r["final_candidate"]),
    "execution_not_authorized": r["final_candidate"].get("execution_authorized") is False,
    "paper_submission_disabled": r["paper_submission_enabled"] is False,
    "live_submission_disabled": r["live_submission_enabled"] is False,
    "broker_write_disabled": r["broker_write_enabled"] is False,
    "paper_orders_zero": r["actual_paper_orders_submitted"] == 0,
    "live_orders_zero": r["actual_live_orders_submitted"] == 0,
    "web_api_present": (ROOT / "web_controller/multi_timeframe_strategy_api.py").exists(),
}
failed = [name for name, passed in checks.items() if not passed]
verification = {
    "verification_stage": "V280.64",
    "verification_status": "PASS" if not failed else "FAIL",
    "state": r["state"],
    "checks": checks,
    "failed": failed,
    "strategy_rows": r["strategy_rows"],
    "allocation": r["allocation"],
    "final_candidate": r["final_candidate"],
    "actual_paper_orders_submitted": 0,
    "actual_live_orders_submitted": 0,
}
print(json.dumps(verification, indent=2, sort_keys=True))
out = ROOT / "release/v271_01_to_v280_64/actual/multi_timeframe_strategy_verification.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(verification, indent=2, sort_keys=True) + "\n", encoding="utf-8")
raise SystemExit(0 if not failed else 1)
