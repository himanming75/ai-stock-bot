from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/r2_windows_scheduler_service_preparation/"
               "actual/r2_readiness_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": result.get("stage") == "R2",
    "status": result.get("status") == "PASS",
    "prepared_state": (
        result.get("state") ==
        "WINDOWS_DEPLOYMENT_PREPARATION_READY"
    ),
    "three_templates": len(result.get("task_templates", [])) == 3,
    "all_disabled": all(
        item.get("enabled") is False
        for item in result.get("task_templates", [])
    ),
    "registration_not_performed": (
        result.get("task_registration_performed") is False
    ),
    "service_not_installed": (
        result.get("windows_service_installed") is False
    ),
    "start_on_boot_off": result.get("start_on_boot_enabled") is False,
    "auto_restart_off": (
        result.get("automatic_broker_restart_enabled") is False
    ),
    "auto_replay_off": (
        result.get("automatic_order_replay_enabled") is False
    ),
    "live_network_off": result.get("live_network_enabled") is False,
    "live_write_off": result.get("live_write_enabled") is False,
    "paper_orders_zero": (
        result.get("actual_paper_orders_submitted") == 0
    ),
    "live_orders_zero": (
        result.get("actual_live_orders_submitted") == 0
    ),
}
verification = {
    "verification_stage": "R2_PREPARATION",
    "verification_status": (
        "PASS" if all(checks.values()) else "FAIL"
    ),
    "checks": checks,
    "failed": [k for k, v in checks.items() if not v],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
