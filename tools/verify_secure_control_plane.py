from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/secure_control_plane_operator_console/actual/"
               "secure_control_plane_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": (
        result.get("stage")
        == "SECURE_CONTROL_PLANE_OPERATOR_CONSOLE_MEGA_BUNDLE"
    ),
    "status": result.get("status") == "PASS",
    "roles_ready": result.get("role_permission_model") == "READY",
    "sessions_preview_only": (
        result.get("session_management") == "READY_PREVIEW_ONLY"
    ),
    "confirmation_preview_only": (
        result.get("two_step_confirmation") == "READY_PREVIEW_ONLY"
    ),
    "strategy_preview_only": (
        result.get("strategy_state_control") == "READY_PREVIEW_ONLY"
    ),
    "runtime_preview_only": (
        result.get("runtime_state_control") == "READY_PREVIEW_ONLY"
    ),
    "kill_switch_preview_only": (
        result.get("kill_switch_control") == "READY_PREVIEW_ONLY"
    ),
    "emergency_preview_only": (
        result.get("emergency_stop_control") == "READY_PREVIEW_ONLY"
    ),
    "console_read_only": (
        result.get("operator_console") == "READY_READ_ONLY"
    ),
    "config_not_applied": (
        result.get("actual_configuration_applied") is False
    ),
    "strategy_not_changed": (
        result.get("actual_strategy_change_performed") is False
    ),
    "runtime_not_started": result.get("actual_runtime_started") is False,
    "runtime_not_stopped": result.get("actual_runtime_stopped") is False,
    "workers_not_scaled": (
        result.get("actual_worker_scale_changed") is False
    ),
    "scheduler_not_changed": (
        result.get("actual_scheduler_changed") is False
    ),
    "kill_switch_not_changed": (
        result.get("actual_kill_switch_changed") is False
    ),
    "emergency_stop_not_activated": (
        result.get("actual_emergency_stop_activated") is False
    ),
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
    "verification_stage": "SECURE_CONTROL_PLANE_OPERATOR_CONSOLE",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [key for key, value in checks.items() if not value],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
