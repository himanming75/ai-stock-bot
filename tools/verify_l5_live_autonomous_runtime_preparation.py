from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/l5_live_autonomous_runtime_preparation/actual/"
               "l5_offline_qualification.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": result.get("stage") == "L5",
    "status": result.get("status") == "PASS",
    "prepared_state": (
        result.get("state") == "LIVE_AUTONOMOUS_RUNTIME_PREPARED"
    ),
    "three_cycles": result.get("completed_cycle_count") == 3,
    "policy_valid": result.get("policy", {}).get("valid") is True,
    "actual_runtime_blocked": (
        result.get("actual_live_runtime_allowed") is False
    ),
    "live_network_off": result.get("live_network_enabled") is False,
    "live_write_off": result.get("live_write_enabled") is False,
    "auto_replay_off": (
        result.get("automatic_order_replay_enabled") is False
    ),
    "auto_restart_off": (
        result.get("automatic_broker_restart_enabled") is False
    ),
    "paper_orders_zero": (
        result.get("actual_paper_orders_submitted") == 0
    ),
    "live_orders_zero": (
        result.get("actual_live_orders_submitted") == 0
    ),
}
verification = {
    "verification_stage": "L5_PREPARATION",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
