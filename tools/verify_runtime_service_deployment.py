from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/runtime_service_deployment/actual/"
               "runtime_service_deployment_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": (
        result.get("stage")
        == "RUNTIME_SERVICE_DEPLOYMENT_DASHBOARD6_MEGA_BUNDLE"
    ),
    "status": result.get("status") == "PASS",
    "service_preview_only": (
        result.get("runtime_service_framework") == "READY_PREVIEW_ONLY"
    ),
    "service_not_installed": (
        result.get("windows_service_installed") is False
    ),
    "auto_start_off": result.get("automatic_start_enabled") is False,
    "auto_restart_off": result.get("automatic_restart_enabled") is False,
    "runtime_not_started": result.get("actual_runtime_started") is False,
    "lock_not_created": result.get("actual_lock_created") is False,
    "pid_not_written": result.get("actual_pid_written") is False,
    "backup_not_performed": (
        result.get("actual_backup_performed") is False
    ),
    "restore_not_performed": (
        result.get("actual_restore_performed") is False
    ),
    "rollback_not_performed": (
        result.get("actual_rollback_performed") is False
    ),
    "release_not_applied": (
        result.get("actual_release_applied") is False
    ),
    "dashboard_read_only": result.get("dashboard_6") == "READY_READ_ONLY",
    "network_unused": result.get("actual_external_network_used") is False,
    "broker_read_unused": (
        result.get("actual_broker_read_performed") is False
    ),
    "broker_write_unused": (
        result.get("actual_broker_write_performed") is False
    ),
    "orders_not_submitted": (
        result.get("actual_order_submission_performed") is False
    ),
    "paper_orders_zero": result.get("actual_paper_orders_submitted") == 0,
    "live_orders_zero": result.get("actual_live_orders_submitted") == 0,
}
verification = {
    "verification_stage": "RUNTIME_SERVICE_DEPLOYMENT_DASHBOARD6",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [key for key, value in checks.items() if not value],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
