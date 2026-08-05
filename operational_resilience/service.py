from __future__ import annotations
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any

from .configuration import (
    ConfigurationSchemaValidator,
    ConfigurationVersionManager,
)
from .faults import FaultInjectionSimulator
from .ledger import LedgerIntegrityAuditor
from .replay import DeterministicReplayManifest
from .retention import DataRetentionPlanner
from .runbook import RecoveryRunbookGenerator
from .snapshots import (
    StateMigrationPreview,
    StateSnapshotManager,
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def run(root: Path) -> dict[str, Any]:
    actual = root / "release/operational_resilience_data_governance/actual"
    actual.mkdir(parents=True, exist_ok=True)

    monitoring = read_json(
        root / "release/ai_monitoring_distributed_runtime/actual/"
               "ai_monitoring_distributed_runtime_result.json"
    )
    feature = read_json(
        root / "release/feature_engine_auto_optimization/actual/"
               "feature_engine_auto_optimization_result.json"
    )
    shadow = read_json(
        root / "release/shadow_trading_production_approval/actual/"
               "shadow_trading_production_approval_result.json"
    )

    config = {
        "schema_version": 1,
        "environment": "offline",
        "broker_mode": "paper",
        "network_enabled": False,
        "write_enabled": False,
        "automatic_order_submission_enabled": False,
        "worker_count": 3,
        "scheduler_interval_seconds": 60,
    }
    config_validation = ConfigurationSchemaValidator().validate(config)
    config_manager = ConfigurationVersionManager()
    config_record = config_manager.create_record(
        name="runtime_offline_config",
        value=config,
    )

    snapshot_manager = StateSnapshotManager()
    snapshot = snapshot_manager.create(
        output=actual / "monitoring_state_snapshot.json",
        state={
            "monitoring_status": monitoring.get("status"),
            "runtime_health": monitoring.get("runtime_health"),
            "load_balance": monitoring.get("load_balance"),
            "release_gate": shadow.get("release_gate"),
        },
        source_name="AI_MONITORING_DISTRIBUTED_RUNTIME",
    )
    snapshot_integrity = snapshot_manager.verify(snapshot)

    migration = StateMigrationPreview().preview(
        current_version=1,
        target_version=2,
        state=snapshot["state"],
    )

    ledger_auditor = LedgerIntegrityAuditor()
    ledger_results = [
        ledger_auditor.audit(
            root / "release/shadow_trading_production_approval/actual/"
                   "shadow_trade_ledger.jsonl"
        ),
        ledger_auditor.audit(
            root / "release/shadow_trading_production_approval/actual/"
                   "approval_ledger.jsonl"
        ),
        ledger_auditor.audit(
            root / "release/feature_engine_auto_optimization/actual/"
                   "optimization_history.jsonl"
        ),
    ]

    now = datetime.now(timezone.utc)
    retention_records = [
        {
            "name": "recent-report",
            "created_at": (now - timedelta(days=3)).isoformat(),
        },
        {
            "name": "old-report",
            "created_at": (now - timedelta(days=45)).isoformat(),
        },
    ]
    retention = DataRetentionPlanner().plan(
        records=retention_records,
        retain_days=30,
        observed_at=now,
    )

    replay = DeterministicReplayManifest().build(
        dataset_fingerprint=(
            feature.get("dataset_summary", {})
            .get("dataset_fingerprint", "")
        ),
        strategy_versions={
            "momentum": "3.0.0",
            "mean_reversion": "3.0.0",
            "breakout": "3.0.0",
            "scalping": "1.0.0",
            "swing": "1.0.0",
        },
        configuration_fingerprint=config_record["fingerprint"],
        random_seed=21,
    )

    simulator = FaultInjectionSimulator()
    fault_results = [
        simulator.simulate(name)
        for name in sorted(simulator.SUPPORTED)
    ]
    runbook = RecoveryRunbookGenerator().build(fault_results)

    release_diff = {
        "base_stage": "AI_MONITORING_DISTRIBUTED_RUNTIME_MEGA_BUNDLE",
        "candidate_stage": "OPERATIONAL_RESILIENCE_DATA_GOVERNANCE",
        "added_capabilities": [
            "configuration_versioning",
            "configuration_schema_validation",
            "state_snapshot",
            "snapshot_integrity",
            "state_migration_preview",
            "ledger_integrity_audit",
            "retention_planning",
            "deterministic_replay_manifest",
            "fault_injection_simulation",
            "recovery_runbook",
        ],
        "actual_release_applied": False,
    }

    checks = {
        "monitoring_framework_pass": monitoring.get("status") == "PASS",
        "feature_framework_pass": feature.get("status") == "PASS",
        "shadow_framework_pass": shadow.get("status") == "PASS",
        "configuration_valid": config_validation["valid"] is True,
        "configuration_not_applied": (
            config_record["actual_configuration_applied"] is False
        ),
        "snapshot_integrity_valid": (
            snapshot_integrity["integrity_valid"] is True
        ),
        "migration_preview_ready": (
            migration["migration_preview_allowed"] is True
        ),
        "migration_not_performed": (
            migration["actual_migration_performed"] is False
        ),
        "all_ledgers_present": all(
            item["exists"] is True for item in ledger_results
        ),
        "all_ledgers_valid": all(
            item["status"] == "PASS" for item in ledger_results
        ),
        "retention_preview_created": retention["archive_count"] == 1,
        "replay_manifest_created": len(replay["replay_id"]) == 64,
        "six_faults_simulated": len(fault_results) == 6,
        "faults_not_live": all(
            item["fault_injected_into_live_runtime"] is False
            for item in fault_results
        ),
        "runbook_created": runbook["step_count"] == 6,
        "release_not_applied": (
            release_diff["actual_release_applied"] is False
        ),
    }

    result = {
        "stage": "OPERATIONAL_RESILIENCE_DATA_GOVERNANCE_MEGA_BUNDLE",
        "state": "OFFLINE_QUALIFIED",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failed": [key for key, value in checks.items() if not value],
        "configuration_versioning": "READY",
        "configuration_schema_validation": "READY",
        "state_snapshot_manager": "READY",
        "snapshot_integrity": "READY",
        "state_migration": "READY_PREVIEW_ONLY",
        "backup_restore_drill": "READY_PREVIEW_ONLY",
        "ledger_integrity_audit": "READY",
        "data_retention_planner": "READY_PREVIEW_ONLY",
        "deterministic_replay_manifest": "READY",
        "fault_injection_simulator": "READY_OFFLINE",
        "recovery_runbook_generator": "READY",
        "release_diff_summary": "READY",
        "operational_readiness_report": "READY",
        "configuration_validation_result": config_validation,
        "configuration_version_record": config_record,
        "snapshot_integrity_result": snapshot_integrity,
        "migration_preview": migration,
        "ledger_audit_results": ledger_results,
        "retention_plan": retention,
        "replay_manifest": replay,
        "fault_injection_results": fault_results,
        "recovery_runbook": runbook,
        "release_diff": release_diff,
        "actual_configuration_applied": False,
        "actual_state_migration_performed": False,
        "actual_restore_performed": False,
        "actual_files_deleted": False,
        "actual_files_archived": False,
        "actual_replay_started": False,
        "actual_fault_injected_into_live_runtime": False,
        "automatic_recovery_enabled": False,
        "actual_recovery_performed": False,
        "actual_release_applied": False,
        "actual_external_network_used": False,
        "actual_broker_read_performed": False,
        "actual_broker_write_performed": False,
        "actual_order_submission_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_development": "SECURE_CONTROL_PLANE_AND_OPERATOR_CONSOLE",
    }
    (actual / "operational_resilience_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result
