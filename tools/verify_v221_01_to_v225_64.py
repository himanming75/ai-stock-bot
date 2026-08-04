import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from paper_operations_v2.engine import evaluate
r = evaluate(ROOT)
checks = {
    "stage": r["stage"] == "V225.64",
    "status": r["status"] == "PASS",
    "allowed_state": r["state"] in {
        "PAPER_OPERATIONS_AUTOMATION_V2_READY",
        "PAPER_OPERATIONS_AUTOMATION_V2_REVIEW_REQUIRED",
    },
    "automation_foundation_ready": r["automatic_cycle_foundation_ready"] is True,
    "paper_submission_default_off": r["paper_submission_enabled"] is False,
    "real_network_default_off": r["real_network_enabled"] is False,
    "paper_orders_zero": r["paper_orders_submitted"] == 0,
    "broker_write_disabled": r["broker_write_enabled"] is False,
    "live_orders_zero": r["actual_live_orders_submitted"] == 0,
    "checkpoint_present": (ROOT / "release/v221_01_to_v225_64/actual/paper_operations_checkpoint.json").exists(),
    "recovery_present": (ROOT / "release/v221_01_to_v225_64/actual/paper_recovery_plan.json").exists(),
    "web_api_present": (ROOT / "web_controller/paper_operations_v2_api.py").exists(),
}
failed = [name for name, passed in checks.items() if not passed]
result = {
    "verification_stage": "V225.64",
    "verification_status": "PASS" if not failed else "FAIL",
    "state": r["state"],
    "cycle_id": r["cycle_id"],
    "checks": checks,
    "failed": failed,
    "order_plan": r["order_plan"],
    "reconciliation": r["reconciliation"],
    "paper_orders_submitted": r["paper_orders_submitted"],
    "actual_live_orders_submitted": 0,
}
print(json.dumps(result, indent=2, sort_keys=True))
out = ROOT / "release/v221_01_to_v225_64/actual/paper_operations_v2_verification.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
raise SystemExit(0 if not failed else 1)
