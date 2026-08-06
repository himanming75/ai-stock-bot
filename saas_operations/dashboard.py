from __future__ import annotations

from .health import HeartbeatRegistry
from .metrics import MetricsRegistry


def build_dashboard(
    *,
    metrics: MetricsRegistry,
    heartbeats: HeartbeatRegistry,
    system: dict,
    notifications: list[dict],
    logs: list[dict],
    backups: list[dict],
) -> dict:
    service_items = [
        item.to_dict()
        for item in heartbeats.snapshot()
    ]
    overall = "HEALTHY"
    if any(
        item["status"] in {
            "FAILED",
            "STALE",
            "STOPPED",
        }
        for item in service_items
    ):
        overall = "DEGRADED"

    return {
        "overall_status": overall,
        "metrics": metrics.snapshot(),
        "services": service_items,
        "system": system,
        "notifications": notifications,
        "recent_logs": logs[:20],
        "backups": backups,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
    }
