from __future__ import annotations
from datetime import datetime, timezone
import json
import platform
from pathlib import Path
from typing import Any

from .error_stats import collect_error_statistics
from .health_score import calculate_health_score
from .latency_stats import collect_latency_statistics
from .scheduler_monitor import scheduler_status
from .watchdog import evaluate_watchdog


def build_diagnostic_report(root: Path) -> dict[str, Any]:
    return {
        "stage": "O3_DIAGNOSTICS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "python_version": platform.python_version(),
        },
        "health": calculate_health_score(root),
        "watchdog": evaluate_watchdog(root),
        "scheduler": scheduler_status(root),
        "latency": collect_latency_statistics(root),
        "errors": collect_error_statistics(root),
        "safety": {
            "automatic_broker_restart_enabled": False,
            "automatic_order_replay_enabled": False,
            "live_network_enabled": False,
            "live_write_enabled": False,
        },
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }
