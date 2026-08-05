from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from .windows_gate import evaluate_windows_activation_gate
from .windows_tasks import export_task_xml


def evaluate_windows_deployment_readiness(
    root: Path,
) -> dict[str, Any]:
    actual = (
        root / "release/r2_windows_scheduler_service_preparation/actual"
    )
    tasks = export_task_xml(
        root,
        actual / "task_xml",
    )
    gate = evaluate_windows_activation_gate(root)

    checks = {
        "three_task_templates_created": len(tasks) == 3,
        "all_tasks_disabled": all(
            item["enabled"] is False for item in tasks
        ),
        "automatic_restart_disabled": all(
            item["restart_count"] == 0 for item in tasks
        ),
        "runtime_wrapper_present": (
            root / "RUN_R2_RUNTIME_WRAPPER.ps1"
        ).exists(),
        "stop_script_present": (
            root / "STOP_R2_RUNTIME.ps1"
        ).exists(),
        "install_preview_present": (
            root / "PREVIEW_R2_TASK_INSTALL.ps1"
        ).exists(),
        "uninstall_script_present": (
            root / "UNINSTALL_R2_TASKS.ps1"
        ).exists(),
    }

    value = {
        "stage": "R2",
        "state": "WINDOWS_DEPLOYMENT_PREPARATION_READY",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "failed": [k for k, v in checks.items() if not v],
        "task_templates": tasks,
        "activation_gate": gate,
        "task_registration_performed": False,
        "windows_service_installed": False,
        "start_on_boot_enabled": False,
        "automatic_broker_restart_enabled": False,
        "automatic_order_replay_enabled": False,
        "live_network_enabled": False,
        "live_write_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
        "next_fixed_stage": (
            "R2_ACTUAL_TASK_REGISTRATION_AFTER_R1_RELEASE_APPROVAL"
        ),
    }

    actual.mkdir(parents=True, exist_ok=True)
    (actual / "r2_readiness_result.json").write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return value
