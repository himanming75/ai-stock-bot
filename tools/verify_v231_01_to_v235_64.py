import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from order_lifecycle_v2.engine import evaluate
r = evaluate(ROOT)
o = r["order"]
checks = {
    "stage": r["stage"] == "V235.64",
    "status": r["status"] == "PASS",
    "allowed_state": r["state"] in {"ORDER_LIFECYCLE_V2_READY", "ORDER_LIFECYCLE_V2_REVIEW_REQUIRED"},
    "client_order_id_present": bool(o["client_order_id"]),
    "broker_mapping_present": (ROOT / "release/v231_01_to_v235_64/actual/order_id_mapping.json").exists(),
    "lifecycle_ledger_present": (ROOT / "release/v231_01_to_v235_64/actual/order_lifecycle_v2_ledger.jsonl").exists(),
    "recovery_present": (ROOT / "release/v231_01_to_v235_64/actual/order_recovery_plan.json").exists(),
    "paper_submission_disabled": r["paper_submission_enabled"] is False,
    "live_submission_disabled": r["live_submission_enabled"] is False,
    "broker_write_disabled": r["broker_write_enabled"] is False,
    "paper_orders_zero": r["actual_paper_orders_submitted"] == 0,
    "live_orders_zero": r["actual_live_orders_submitted"] == 0,
    "web_api_present": (ROOT / "web_controller/order_lifecycle_v2_api.py").exists(),
}
failed = [k for k, v in checks.items() if not v]
result = {
    "verification_stage": "V235.64",
    "verification_status": "PASS" if not failed else "FAIL",
    "state": r["state"],
    "checks": checks,
    "failed": failed,
    "order": o,
    "duplicate": r["duplicate"],
    "event_count": len(r["events"]),
    "actual_paper_orders_submitted": 0,
    "actual_live_orders_submitted": 0,
}
print(json.dumps(result, indent=2, sort_keys=True))
out = ROOT / "release/v231_01_to_v235_64/actual/order_lifecycle_v2_verification.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
raise SystemExit(0 if not failed else 1)
