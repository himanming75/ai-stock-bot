from __future__ import annotations
from typing import Any


def build_supervisor_policy() -> dict[str, Any]:
    return {
        "stage": "R1_PROCESS_SUPERVISOR_POLICY",
        "start_on_boot_enabled": False,
        "automatic_broker_restart_enabled": False,
        "automatic_order_replay_enabled": False,
        "maximum_restart_attempts": 0,
        "health_check_interval_seconds": 60,
        "shutdown_grace_seconds": 30,
        "restart_requires": [
            "OPERATOR_REVIEW",
            "FRESH_PREFLIGHT",
            "NO_DUPLICATE_RUNTIME_LOCK",
            "NO_UNRECONCILED_BROKER_STATE",
        ],
        "valid": True,
    }
