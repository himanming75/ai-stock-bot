from __future__ import annotations
import os
from pathlib import Path
import shutil
from typing import Any


class RuntimeDiagnostics:
    def collect(self, *, root: Path) -> dict[str, Any]:
        usage = shutil.disk_usage(root)
        cpu_count = os.cpu_count() or 1
        return {
            "cpu_logical_count": cpu_count,
            "memory_detection_mode": "STANDARD_LIBRARY_LIMITED",
            "memory_total_bytes": None,
            "memory_available_bytes": None,
            "disk_total_bytes": usage.total,
            "disk_used_bytes": usage.used,
            "disk_free_bytes": usage.free,
            "process_running": False,
            "runtime_pid": None,
            "actual_process_started": False,
            "actual_external_network_used": False,
        }


class RuntimeHealthAggregator:
    def evaluate(
        self,
        *,
        diagnostics: dict[str, Any],
        monitoring: dict[str, Any],
        control_plane: dict[str, Any],
    ) -> dict[str, Any]:
        checks = {
            "cpu_detected": diagnostics["cpu_logical_count"] >= 1,
            "disk_free_positive": diagnostics["disk_free_bytes"] > 0,
            "monitoring_pass": monitoring.get("status") == "PASS",
            "control_plane_pass": control_plane.get("status") == "PASS",
            "broker_write_off": (
                control_plane.get("actual_broker_write_performed") is False
            ),
            "orders_zero": (
                control_plane.get("actual_paper_orders_submitted") == 0
                and control_plane.get("actual_live_orders_submitted") == 0
            ),
        }
        return {
            "checks": checks,
            "failed": [key for key, value in checks.items() if not value],
            "status": "PASS" if all(checks.values()) else "FAIL",
            "actual_recovery_performed": False,
        }
