import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from live_shadow_slippage.engine import evaluate
r = evaluate(ROOT)
checks = {
    "stage": r["stage"] == "V230.64",
    "status": r["status"] == "PASS",
    "allowed_state": r["state"] in {"LIVE_SHADOW_QUALIFIED", "LIVE_SHADOW_REVIEW_REQUIRED"},
    "quote_present": bool(r["quote"]),
    "slippage_present": bool(r["slippage"]),
    "qualification_present": bool(r["qualification"]),
    "live_submission_disabled": r["live_submission_enabled"] is False,
    "broker_write_disabled": r["broker_write_enabled"] is False,
    "live_orders_zero": r["actual_live_orders_submitted"] == 0,
    "web_api_present": (ROOT / "web_controller/live_shadow_api.py").exists(),
}
failed = [name for name, passed in checks.items() if not passed]
result = {
    "verification_stage": "V230.64",
    "verification_status": "PASS" if not failed else "FAIL",
    "state": r["state"],
    "checks": checks,
    "failed": failed,
    "quote": r["quote"],
    "slippage": r["slippage"],
    "qualification": r["qualification"],
    "daily_report": r["daily_report"],
    "actual_live_orders_submitted": 0,
}
print(json.dumps(result, indent=2, sort_keys=True))
out = ROOT / "release/v226_01_to_v230_64/actual/live_shadow_slippage_verification.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
raise SystemExit(0 if not failed else 1)
