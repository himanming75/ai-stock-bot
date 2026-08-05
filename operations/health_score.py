from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .metrics import collect_metrics
from .scheduler_monitor import scheduler_status
from .status_reader import collect_status
from .watchdog import evaluate_watchdog


def calculate_health_score(root: Path) -> dict[str, Any]:
    status = collect_status(root)
    watchdog = evaluate_watchdog(root)
    scheduler = scheduler_status(root)
    metrics = collect_metrics(root)

    checks = {
        "paper_mode": status["mode"].get("paper") is True,
        "live_mode_disabled": status["mode"].get("live") is False,
        "live_activation_blocked": (
            status["mode"].get("live_activation_allowed") is False
        ),
        "kill_switch_readable": (
            "kill_switch_active" in status.get("kill_switch", {})
        ),
        "watchdog_pass": watchdog.get("status") == "PASS",
        "scheduler_pass": scheduler.get("status") == "PASS",
        "live_network_disabled": (
            metrics.get("live_network_enabled") is False
        ),
        "live_write_disabled": (
            metrics.get("live_write_enabled") is False
        ),
    }

    weights = {
        "paper_mode": 10,
        "live_mode_disabled": 20,
        "live_activation_blocked": 20,
        "kill_switch_readable": 10,
        "watchdog_pass": 15,
        "scheduler_pass": 15,
        "live_network_disabled": 5,
        "live_write_disabled": 5,
    }

    score = sum(
        weights[name] for name, passed in checks.items() if passed
    )
    failed = [name for name, passed in checks.items() if not passed]
    if score >= 90:
        state = "HEALTHY"
    elif score >= 70:
        state = "DEGRADED"
    else:
        state = "BLOCKED"

    return {
        "stage": "O3_HEALTH_SCORE",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "score": score,
        "maximum_score": 100,
        "state": state,
        "checks": checks,
        "failed": failed,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }
