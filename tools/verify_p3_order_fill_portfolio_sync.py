from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT
        / "release/p3_order_fill_portfolio_sync/actual/"
          "p3_sync_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": result.get("stage") == "P3",
    "status": result.get("status") == "PASS",
    "state": result.get("state") == "ORDER_FILL_PORTFOLIO_SYNC_READY",
    "reconciliation": result.get("reconciliation_passed") is True,
    "new_orders_allowed": result.get("new_order_submission_allowed") is True,
    "new_fill_count": result.get("new_fill_count") == 1,
    "no_unknown_states": result.get("unknown_order_states") == [],
    "no_position_drift": result.get("position_drifts") == [],
    "no_account_drift": result.get("account_drifts") == [],
    "broker_write_off": result.get("broker_write_enabled") is False,
    "paper_submission_off": result.get("paper_submission_enabled") is False,
    "live_submission_off": result.get("live_submission_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
    "next_fixed_stage": (
        result.get("next_fixed_stage")
        == "P4_AUTONOMOUS_PAPER_RUNTIME"
    ),
}

verification = {
    "verification_stage": "P3",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [name for name, passed in checks.items() if not passed],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
