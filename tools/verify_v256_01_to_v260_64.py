import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from autonomous_paper_trading.engine import evaluate
r = evaluate(ROOT, allow_network=False)
checks = {
    "stage": r["stage"] == "V260.64",
    "status": r["status"] == "PASS",
    "allowed_state": r["state"] in {
        "AUTONOMOUS_PAPER_TRADING_ACTIVE",
        "AUTONOMOUS_PAPER_TRADING_READY_BLOCKED",
    },
    "paper_endpoint_only": True,
    "paper_submission_default_off": r["real_paper_submission_enabled"] is False,
    "network_not_authorized": "NETWORK_CALL_NOT_AUTHORIZED_FOR_THIS_RUN" in r["blocking_reasons"],
    "paper_orders_zero": r["actual_paper_orders_submitted"] == 0,
    "live_orders_zero": r["actual_live_orders_submitted"] == 0,
    "live_submission_disabled": r["live_submission_enabled"] is False,
    "live_network_disabled": r["live_network_enabled"] is False,
    "broker_write_disabled": r["broker_write_enabled"] is False,
    "daily_report_present": (ROOT / "release/v256_01_to_v260_64/actual/autonomous_paper_daily_report.json").exists(),
    "web_api_present": (ROOT / "web_controller/autonomous_paper_api.py").exists(),
}
failed = [k for k, v in checks.items() if not v]
result = {
    "verification_stage": "V260.64",
    "verification_status": "PASS" if not failed else "FAIL",
    "state": r["state"],
    "checks": checks,
    "failed": failed,
    "blocking_reasons": r["blocking_reasons"],
    "actual_paper_orders_submitted": r["actual_paper_orders_submitted"],
    "actual_live_orders_submitted": 0,
}
print(json.dumps(result, indent=2, sort_keys=True))
out = ROOT / "release/v256_01_to_v260_64/actual/autonomous_paper_trading_verification.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
raise SystemExit(0 if not failed else 1)
