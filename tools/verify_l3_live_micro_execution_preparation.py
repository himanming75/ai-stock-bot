from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/l3_live_micro_execution_preparation/actual/"
               "l3_offline_qualification.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": result.get("stage") == "L3",
    "status": result.get("status") == "PASS",
    "prepared_state": result.get("state") == "LIVE_MICRO_EXECUTION_PREPARED",
    "submitted_false": result.get("submitted") is False,
    "actual_live_execution_blocked": (
        result.get("actual_live_execution_allowed") is False
    ),
    "dry_run": result.get("dry_run", {}).get("dry_run") is True,
    "network_unused": (
        result.get("dry_run", {}).get("broker_network_used") is False
    ),
    "live_write_off": result.get("live_write_enabled") is False,
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
    "auto_replay_off": (
        result.get("rollback_plan", {}).get(
            "automatic_order_replay_enabled"
        ) is False
    ),
}
verification = {
    "verification_stage": "L3_PREPARATION",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
