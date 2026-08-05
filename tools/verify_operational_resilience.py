from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
result = json.loads(
    (
        ROOT / "release/operational_resilience_data_governance/actual/"
               "operational_resilience_result.json"
    ).read_text(encoding="utf-8-sig")
)

checks = {
    "stage": (
        result.get("stage")
        == "OPERATIONAL_RESILIENCE_DATA_GOVERNANCE_MEGA_BUNDLE"
    ),
    "status": result.get("status") == "PASS",
    "config_ready": result.get("configuration_versioning") == "READY",
    "snapshot_ready": result.get("state_snapshot_manager") == "READY",
    "integrity_ready": result.get("snapshot_integrity") == "READY",
    "migration_preview_only": (
        result.get("state_migration") == "READY_PREVIEW_ONLY"
    ),
    "ledger_audit_ready": (
        result.get("ledger_integrity_audit") == "READY"
    ),
    "retention_preview_only": (
        result.get("data_retention_planner") == "READY_PREVIEW_ONLY"
    ),
    "replay_ready": (
        result.get("deterministic_replay_manifest") == "READY"
    ),
    "fault_simulator_offline": (
        result.get("fault_injection_simulator") == "READY_OFFLINE"
    ),
    "runbook_ready": (
        result.get("recovery_runbook_generator") == "READY"
    ),
    "configuration_not_applied": (
        result.get("actual_configuration_applied") is False
    ),
    "migration_not_performed": (
        result.get("actual_state_migration_performed") is False
    ),
    "restore_not_performed": (
        result.get("actual_restore_performed") is False
    ),
    "files_not_deleted": result.get("actual_files_deleted") is False,
    "files_not_archived": result.get("actual_files_archived") is False,
    "replay_not_started": result.get("actual_replay_started") is False,
    "fault_not_live": (
        result.get("actual_fault_injected_into_live_runtime") is False
    ),
    "recovery_off": (
        result.get("automatic_recovery_enabled") is False
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
    "verification_stage": "OPERATIONAL_RESILIENCE_DATA_GOVERNANCE",
    "verification_status": "PASS" if all(checks.values()) else "FAIL",
    "checks": checks,
    "failed": [key for key, value in checks.items() if not value],
}
print(json.dumps(verification, indent=2, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
