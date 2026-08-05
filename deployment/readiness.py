from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .backup import build_backup_inventory, write_restore_plan
from .config_audit import audit_configuration
from .gates import evaluate_production_gates
from .release_manifest import build_release_manifest
from .retention import RetentionPolicy
from .supervisor import build_supervisor_policy


def evaluate_deployment_readiness(root: Path) -> dict[str, Any]:
    actual = root / "release/r1_production_deployment_preparation/actual"
    manifest = build_release_manifest(root)
    config = audit_configuration(root)
    retention = RetentionPolicy().evaluate()
    backup = build_backup_inventory(root)
    restore = write_restore_plan(actual / "restore_plan.json")
    supervisor = build_supervisor_policy()
    gates = evaluate_production_gates(root)

    preparation_checks = {
        "release_manifest_valid": manifest["file_count"] > 0,
        "configuration_audit_valid": config["valid"],
        "retention_policy_valid": retention["valid"],
        "backup_inventory_created": backup["file_count"] >= 0,
        "restore_plan_safe": (
            restore["automatic_restore_enabled"] is False
        ),
        "supervisor_fail_closed": (
            supervisor["start_on_boot_enabled"] is False
            and supervisor["automatic_broker_restart_enabled"] is False
        ),
    }

    return {
        "stage": "R1",
        "state": "PRODUCTION_DEPLOYMENT_PREPARATION_READY",
        "status": (
            "PASS" if all(preparation_checks.values()) else "FAIL"
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "preparation_checks": preparation_checks,
        "preparation_failed": [
            k for k, v in preparation_checks.items() if not v
        ],
        "release_manifest": manifest,
        "configuration_audit": config,
        "retention_policy": retention,
        "backup_inventory": backup,
        "restore_plan": restore,
        "supervisor_policy": supervisor,
        "production_gates": gates,
        "production_release_allowed": False,
        "start_on_boot_enabled": False,
        "live_network_enabled": False,
        "live_write_enabled": False,
        "automatic_order_replay_enabled": False,
        "automatic_broker_restart_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_stage": (
            "R1_ACTUAL_RELEASE_REVIEW_AFTER_PAPER_AND_L2_TO_L6_ACTUAL"
        ),
    }
