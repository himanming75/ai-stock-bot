from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/l4_live_reconciliation_preparation/actual/"
               "l4_offline_qualification.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": result.get("stage") == "L4",
    "status": result.get("status") == "PASS",
    "prepared_state": result.get("state") == "LIVE_RECONCILIATION_PREPARED",
    "actual_reconciliation_blocked": (
        result.get("actual_live_reconciliation_allowed") is False
    ),
    "actual_reconciliation_not_performed": (
        result.get("actual_live_reconciliation_performed") is False
    ),
    "order_no_drift": (
        result.get("order_reconciliation", {}).get(
            "drift_detected"
        ) is False
    ),
    "position_no_drift": (
        result.get("position_reconciliation", {}).get(
            "drift_detected"
        ) is False
    ),
    "cash_no_drift": (
        result.get("cash_reconciliation", {}).get(
            "drift_detected"
        ) is False
    ),
    "auto_repair_off": (
        result.get("repair_plan", {}).get(
            "automatic_repair_enabled"
        ) is False
    ),
    "auto_replay_off": (
        result.get("repair_plan", {}).get(
            "automatic_order_replay_enabled"
        ) is False
    ),
    "live_network_off": result.get("live_network_enabled") is False,
    "live_write_off": result.get("live_write_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}
verification = {
    "verification_stage": "L4_PREPARATION",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
