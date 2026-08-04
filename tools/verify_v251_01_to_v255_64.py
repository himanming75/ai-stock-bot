import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from execution_optimizer.engine import evaluate
r = evaluate(ROOT)
checks = {
    "stage": r["stage"] == "V255.64",
    "status": r["status"] == "PASS",
    "allowed_state": r["state"] in {"EXECUTION_OPTIMIZER_READY", "EXECUTION_OPTIMIZER_REVIEW_REQUIRED"},
    "quote_present": bool(r["quote"]),
    "fill_probability_present": bool(r["fill_probability"]),
    "slippage_present": bool(r["slippage"]),
    "execution_plan_present": bool(r["execution_plan"]),
    "retry_plan_present": bool(r["retry_plan"]),
    "execution_not_authorized": r["execution_authorized"] is False,
    "paper_submission_disabled": r["paper_submission_enabled"] is False,
    "live_submission_disabled": r["live_submission_enabled"] is False,
    "broker_write_disabled": r["broker_write_enabled"] is False,
    "paper_orders_zero": r["actual_paper_orders_submitted"] == 0,
    "live_orders_zero": r["actual_live_orders_submitted"] == 0,
    "web_api_present": (ROOT / "web_controller/execution_optimizer_api.py").exists(),
}
failed = [k for k, v in checks.items() if not v]
result = {
    "verification_stage": "V255.64",
    "verification_status": "PASS" if not failed else "FAIL",
    "state": r["state"],
    "checks": checks,
    "failed": failed,
    "quote": r["quote"],
    "fill_probability": r["fill_probability"],
    "slippage": r["slippage"],
    "execution_plan": r["execution_plan"],
    "retry_plan": r["retry_plan"],
    "actual_paper_orders_submitted": 0,
    "actual_live_orders_submitted": 0,
}
print(json.dumps(result, indent=2, sort_keys=True))
out = ROOT / "release/v251_01_to_v255_64/actual/execution_optimizer_verification.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
raise SystemExit(0 if not failed else 1)
