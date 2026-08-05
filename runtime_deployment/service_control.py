from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


class RuntimeLockManager:
    def preview(self, *, root: Path, runtime_name: str) -> dict[str, Any]:
        lock_path = root / "release/runtime_service_deployment/actual/runtime.lock"
        pid_path = root / "release/runtime_service_deployment/actual/runtime.pid"
        return {
            "runtime_name": runtime_name,
            "lock_path": str(lock_path),
            "pid_path": str(pid_path),
            "lock_present": lock_path.exists(),
            "pid_present": pid_path.exists(),
            "actual_lock_created": False,
            "actual_pid_written": False,
        }


class RuntimeServicePreview:
    def build(
        self,
        *,
        runtime_name: str,
        start_command: str,
        stop_command: str,
    ) -> dict[str, Any]:
        service_id = hashlib.sha256(
            f"{runtime_name}:{start_command}:{stop_command}".encode("utf-8")
        ).hexdigest()[:24]
        return {
            "service_id": "svc-" + service_id,
            "runtime_name": runtime_name,
            "start_command": start_command,
            "stop_command": stop_command,
            "start_mode": "MANUAL_PREVIEW",
            "automatic_start_enabled": False,
            "automatic_restart_enabled": False,
            "service_install_performed": False,
            "service_start_performed": False,
            "service_stop_performed": False,
            "service_remove_performed": False,
        }


class GracefulShutdownPreview:
    def create(self, *, timeout_seconds: int) -> dict[str, Any]:
        if timeout_seconds < 5 or timeout_seconds > 300:
            raise ValueError("SHUTDOWN_TIMEOUT_OUT_OF_RANGE")
        return {
            "timeout_seconds": timeout_seconds,
            "steps": [
                "STOP_ACCEPTING_NEW_TASKS",
                "WAIT_FOR_ACTIVE_WORKERS",
                "FLUSH_LEDGER_PREVIEW",
                "WRITE_FINAL_HEALTH_PREVIEW",
                "RELEASE_RUNTIME_LOCK_PREVIEW",
            ],
            "actual_shutdown_performed": False,
            "actual_process_terminated": False,
        }


class AutoRestartPolicyPreview:
    def create(
        self,
        *,
        maximum_restarts: int,
        window_minutes: int,
        delay_seconds: int,
    ) -> dict[str, Any]:
        if maximum_restarts < 0 or maximum_restarts > 5:
            raise ValueError("RESTART_COUNT_OUT_OF_RANGE")
        return {
            "maximum_restarts": maximum_restarts,
            "window_minutes": window_minutes,
            "delay_seconds": delay_seconds,
            "automatic_restart_enabled": False,
            "actual_restart_performed": False,
            "operator_approval_required": True,
        }
