import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from real_paper_micro_order.engine import evaluate

r = evaluate(ROOT, allow_network=False, allow_submission=False)
checks = {
    "stage": r["stage"] == "V310.64",
    "status": r["status"] == "PASS",
    "allowed_state": r["state"] in {
        "REAL_PAPER_MICRO_ORDER_SUBMITTED",
        "REAL_PAPER_MICRO_ORDER_READY_BLOCKED",
    },
    "network_blocked": "NETWORK_NOT_AUTHORIZED" in r["blocking_reasons"],
    "submission_blocked": "SUBMISSION_NOT_AUTHORIZED" in r["blocking_reasons"],
    "paper_orders_zero": r["actual_paper_orders_submitted"] == 0,
    "live_orders_zero": r["actual_live_orders_submitted"] == 0,
    "live_submission_disabled": r["live_submission_enabled"] is False,
}
failed = [k for k, v in checks.items() if not v]
v = {
    "verification_stage": "V310.64",
    "verification_status": "PASS" if not failed else "FAIL",
    "state": r["state"],
    "checks": checks,
    "failed": failed,
}
print(json.dumps(v, indent=2, sort_keys=True))
out = ROOT / "release/v306_01_to_v310_64/actual/real_paper_micro_order_verification.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(v, indent=2, sort_keys=True) + "\n", encoding="utf-8")
raise SystemExit(0 if not failed else 1)
