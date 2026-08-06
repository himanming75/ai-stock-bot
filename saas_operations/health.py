from __future__ import annotations
import os
import shutil
import threading
import time
from pathlib import Path

from .models import ServiceStatus


class HeartbeatRegistry:
    def __init__(self) -> None:
        self.heartbeats: dict[str, dict] = {}

    def beat(
        self,
        service_name: str,
        *,
        status: str = "RUNNING",
        restart_count: int = 0,
        message: str = "OK",
    ) -> None:
        self.heartbeats[service_name] = {
            "timestamp": time.time(),
            "status": status,
            "restart_count": restart_count,
            "message": message,
        }

    def snapshot(
        self,
        *,
        stale_after_seconds: float = 90.0,
    ) -> list[ServiceStatus]:
        now = time.time()
        results = []
        for service_name, value in sorted(
            self.heartbeats.items()
        ):
            age = now - value["timestamp"]
            status = value["status"]
            if age > stale_after_seconds:
                status = "STALE"
            results.append(
                ServiceStatus(
                    service_name=service_name,
                    status=status,
                    heartbeat_age_seconds=round(
                        age,
                        3,
                    ),
                    restart_count=int(
                        value["restart_count"]
                    ),
                    message=value["message"],
                )
            )
        return results


def system_health(
    *,
    runtime_path: Path,
) -> dict:
    usage = shutil.disk_usage(
        runtime_path
        if runtime_path.exists()
        else runtime_path.parent
    )
    load_average = (
        os.getloadavg()
        if hasattr(os, "getloadavg")
        else (0.0, 0.0, 0.0)
    )
    return {
        "process_id": os.getpid(),
        "thread_count": threading.active_count(),
        "disk_total_bytes": usage.total,
        "disk_used_bytes": usage.used,
        "disk_free_bytes": usage.free,
        "disk_used_percent": (
            usage.used / usage.total * 100
            if usage.total else 0.0
        ),
        "load_average_1m": load_average[0],
        "load_average_5m": load_average[1],
        "load_average_15m": load_average[2],
    }
