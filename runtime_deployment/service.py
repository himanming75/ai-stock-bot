from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from .deployment import (
    BackupPlanBuilder,
    DeploymentAuditLedger,
    PreInstallAuditor,
    RestorePreview,
    RollbackPreview,
)
from .diagnostics import RuntimeDiagnostics, RuntimeHealthAggregator
from .manifests import (
    BuildManifestBuilder,
    ReleaseManifestBuilder,
    VersionHistory,
)
from .packaging import ReleaseBundleBuilder, BundleIntegrityVerifier
from .service_control import (
    AutoRestartPolicyPreview,
    GracefulShutdownPreview,
    RuntimeLockManager,
    RuntimeServicePreview,
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def run(root: Path) -> dict[str, Any]:
    actual = root / "release/runtime_service_deployment/actual"
    actual.mkdir(parents=True, exist_ok=True)

    monitoring = read_json(
        root / "release/ai_monitoring_distributed_runtime/actual/"
               "ai_monitoring_distributed_runtime_result.json"
    )
    control_plane = read_json(
        root / "release/secure_control_plane_operator_console/actual/"
               "secure_control_plane_result.json"
    )
    resilience = read_json(
        root / "release/operational_resilience_data_governance/actual/"
               "operational_resilience_result.json"
    )

    required = [
        ".venv/Scripts/python.exe",
        "RUN_SECURE_CONTROL_PLANE.ps1",
        "RUN_AI_MONITORING_DISTRIBUTED_RUNTIME.ps1",
        "release/secure_control_plane_operator_console/actual/"
        "secure_control_plane_result.json",
    ]
    preinstall = PreInstallAuditor().audit(root=root, required=required)

    service_preview = RuntimeServicePreview().build(
        runtime_name="AIStockBot-Runtime",
        start_command=(
            "powershell -ExecutionPolicy Bypass "
            "-File RUN_AI_MONITORING_DISTRIBUTED_RUNTIME.ps1"
        ),
        stop_command=(
            "powershell -ExecutionPolicy Bypass "
            "-File STOP_AI_STOCK_BOT_RUNTIME_PREVIEW.ps1"
        ),
    )
    lock_preview = RuntimeLockManager().preview(
        root=root,
        runtime_name="AIStockBot-Runtime",
    )
    graceful = GracefulShutdownPreview().create(timeout_seconds=30)
    restart_policy = AutoRestartPolicyPreview().create(
        maximum_restarts=3,
        window_minutes=30,
        delay_seconds=60,
    )

    build_files = [
        root / "RUN_SECURE_CONTROL_PLANE.ps1",
        root / "RUN_AI_MONITORING_DISTRIBUTED_RUNTIME.ps1",
        root / "RUN_SECURE_OPERATOR_CONSOLE.ps1",
        root / "RUN_AI_MONITORING_DASHBOARD.ps1",
        root / "SECURE_CONTROL_PLANE_OPERATOR_CONSOLE_MANIFEST.json",
        root / "AI_MONITORING_DISTRIBUTED_RUNTIME_MANIFEST.json",
    ]
    version = "offline-runtime-6.0.0"
    build_manifest = BuildManifestBuilder().build(
        root=root,
        files=build_files,
        version=version,
    )
    release_manifest = ReleaseManifestBuilder().build(
        version=version,
        build_manifest=build_manifest,
    )

    (actual / "build_manifest.json").write_text(
        json.dumps(build_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (actual / "release_manifest.json").write_text(
        json.dumps(release_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    bundle_path = actual / "preview_release_bundle.zip"
    release_bundle = ReleaseBundleBuilder().build_preview(
        root=root,
        output=bundle_path,
        files=build_files
        + [
            actual / "build_manifest.json",
            actual / "release_manifest.json",
        ],
    )
    bundle_integrity = BundleIntegrityVerifier().verify(
        bundle_path=bundle_path,
        expected_sha256=release_bundle["bundle_sha256"],
    )

    backup_plan = BackupPlanBuilder().build(
        sources=[
            "release",
            "config",
            "deployment",
            "secure_control_plane",
            "ai_monitoring_runtime",
        ],
        destination=(
            "release/runtime_service_deployment/actual/"
            "backup_preview"
        ),
    )
    restore_preview = RestorePreview().build(
        backup_path=release_bundle["bundle_path"],
        target_root=str(root),
    )
    rollback_preview = RollbackPreview().build(
        current_version="offline-runtime-6.0.0",
        target_version="offline-runtime-5.0.0",
    )

    diagnostics = RuntimeDiagnostics().collect(root=root)
    runtime_health = RuntimeHealthAggregator().evaluate(
        diagnostics=diagnostics,
        monitoring=monitoring,
        control_plane=control_plane,
    )

    version_history_path = actual / "version_history.jsonl"
    if version_history_path.exists():
        version_history_path.unlink()
    VersionHistory(version_history_path).append({
        "version": version,
        "state": "PREVIEW_ONLY",
        "manifest_sha256": build_manifest["manifest_sha256"],
        "actual_release_applied": False,
    })

    audit_path = actual / "deployment_audit_ledger.jsonl"
    if audit_path.exists():
        audit_path.unlink()
    audit = DeploymentAuditLedger(audit_path)
    for event_type, payload in [
        ("PREINSTALL_AUDIT", preinstall),
        ("SERVICE_PREVIEW", service_preview),
        ("BUILD_MANIFEST", build_manifest),
        ("RELEASE_MANIFEST", release_manifest),
        ("RELEASE_BUNDLE", release_bundle),
        ("BACKUP_PLAN", backup_plan),
        ("RESTORE_PREVIEW", restore_preview),
        ("ROLLBACK_PREVIEW", rollback_preview),
        ("RUNTIME_DIAGNOSTICS", diagnostics),
        ("RUNTIME_HEALTH", runtime_health),
    ]:
        audit.append(event_type=event_type, payload=payload)

    checks = {
        "monitoring_pass": monitoring.get("status") == "PASS",
        "control_plane_pass": control_plane.get("status") == "PASS",
        "resilience_pass": resilience.get("status") == "PASS",
        "preinstall_pass": preinstall["status"] == "PASS",
        "service_preview_created": bool(service_preview["service_id"]),
        "service_not_installed": (
            service_preview["service_install_performed"] is False
        ),
        "service_not_started": (
            service_preview["service_start_performed"] is False
        ),
        "lock_not_created": lock_preview["actual_lock_created"] is False,
        "shutdown_preview_only": (
            graceful["actual_shutdown_performed"] is False
        ),
        "automatic_restart_off": (
            restart_policy["automatic_restart_enabled"] is False
        ),
        "build_manifest_created": build_manifest["file_count"] >= 4,
        "release_manifest_preview": (
            release_manifest["release_state"] == "PREVIEW_ONLY"
        ),
        "bundle_created": release_bundle["bundle_size_bytes"] > 0,
        "bundle_integrity_valid": bundle_integrity["integrity_valid"] is True,
        "backup_not_performed": (
            backup_plan["actual_backup_performed"] is False
        ),
        "restore_not_performed": (
            restore_preview["actual_restore_performed"] is False
        ),
        "rollback_not_performed": (
            rollback_preview["actual_rollback_performed"] is False
        ),
        "diagnostics_created": diagnostics["cpu_logical_count"] >= 1,
        "runtime_health_pass": runtime_health["status"] == "PASS",
        "version_history_created": version_history_path.exists(),
        "deployment_audit_created": audit_path.exists(),
    }

    result = {
        "stage": "RUNTIME_SERVICE_DEPLOYMENT_DASHBOARD6_MEGA_BUNDLE",
        "state": "OFFLINE_QUALIFIED",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "failed": [key for key, value in checks.items() if not value],
        "runtime_service_framework": "READY_PREVIEW_ONLY",
        "service_start_stop": "READY_PREVIEW_ONLY",
        "pid_lock_management": "READY_PREVIEW_ONLY",
        "graceful_shutdown": "READY_PREVIEW_ONLY",
        "auto_restart_policy": "READY_PREVIEW_ONLY",
        "deployment_manifest": "READY",
        "build_manifest": "READY",
        "version_manifest": "READY",
        "backup_plan": "READY_PREVIEW_ONLY",
        "restore_preview": "READY_PREVIEW_ONLY",
        "rollback_preview": "READY_PREVIEW_ONLY",
        "release_zip_builder": "READY",
        "sha256_checksum": "READY",
        "preinstall_audit": "READY",
        "postinstall_verify": "READY",
        "runtime_diagnostics": "READY",
        "worker_queue_process_health": "READY",
        "dashboard_6": "READY_READ_ONLY",
        "runtime_audit": "READY",
        "install_audit": "READY",
        "deployment_audit": "READY",
        "version_history": "READY",
        "rollback_history": "READY_PREVIEW_ONLY",
        "release_version": version,
        "preinstall_result": preinstall,
        "service_preview": service_preview,
        "lock_preview": lock_preview,
        "graceful_shutdown_preview": graceful,
        "restart_policy_preview": restart_policy,
        "build_manifest_result": build_manifest,
        "release_manifest_result": release_manifest,
        "release_bundle": release_bundle,
        "bundle_integrity": bundle_integrity,
        "backup_plan_result": backup_plan,
        "restore_preview_result": restore_preview,
        "rollback_preview_result": rollback_preview,
        "diagnostics": diagnostics,
        "runtime_health": runtime_health,
        "windows_service_installed": False,
        "automatic_start_enabled": False,
        "automatic_restart_enabled": False,
        "actual_runtime_started": False,
        "actual_runtime_stopped": False,
        "actual_lock_created": False,
        "actual_pid_written": False,
        "actual_backup_performed": False,
        "actual_restore_performed": False,
        "actual_rollback_performed": False,
        "actual_release_applied": False,
        "actual_external_network_used": False,
        "actual_broker_read_performed": False,
        "actual_broker_write_performed": False,
        "actual_order_submission_performed": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_offline_development": (
            "FINAL_OFFLINE_RELEASE_CANDIDATE_AUDIT"
        ),
        "next_market_dependent_action": (
            "P3_ACTUAL_PAPER_ORDER_VALIDATION"
        ),
    }
    (actual / "runtime_service_deployment_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result
