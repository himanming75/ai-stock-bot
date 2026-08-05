from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
actual = ROOT / "release/o2_operations_enhancement/actual"
watchdog = json.loads((actual / "watchdog_result.json").read_text(encoding="utf-8-sig"))
scheduler = json.loads((actual / "scheduler_result.json").read_text(encoding="utf-8-sig"))
recovery = json.loads((actual / "recovery_snapshot.json").read_text(encoding="utf-8-sig"))

checks = {
    "watchdog_pass": watchdog.get("status") == "PASS",
    "scheduler_pass": scheduler.get("status") == "PASS",
    "auto_order_replay_off": (
        recovery.get("automatic_order_replay_enabled") is False
    ),
    "auto_broker_restart_off": (
        recovery.get("automatic_broker_restart_enabled") is False
    ),
    "safe_auto_resume_off": recovery.get("safe_to_auto_resume") is False,
    "live_orders_zero": (
        watchdog.get("actual_live_orders_submitted") == 0
        and scheduler.get("actual_live_orders_submitted") == 0
        and recovery.get("actual_live_orders_submitted") == 0
    ),
}
result = {
    "verification_stage": "O2",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [key for key, value in checks.items() if not value],
}
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
