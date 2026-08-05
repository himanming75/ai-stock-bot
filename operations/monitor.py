from __future__ import annotations
from datetime import datetime, timezone
import shutil
from pathlib import Path
from typing import Any

from .jsonlog import JsonEventLogger
from .status_reader import collect_status


def monitor_once(root: Path) -> dict[str, Any]:
    status = collect_status(root)
    free_disk = shutil.disk_usage(root).free
    kill_active = status["kill_switch"].get(
        "kill_switch_active",
        True,
    )

    checks = {
        "free_disk_over_250mb": free_disk >= 250_000_000,
        "kill_switch_state_readable": (
            "kill_switch_active" in status["kill_switch"]
        ),
        "live_mode_disabled": (
            status["mode"]["live"] is False
        ),
        "live_activation_blocked": (
            status["mode"]["live_activation_allowed"] is False
        ),
    }
    alerts = [
        name for name, passed in checks.items() if not passed
    ]
    severity = "CRITICAL" if alerts else "OK"

    result = {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "severity": severity,
        "checks": checks,
        "alerts": alerts,
        "free_disk_bytes": free_disk,
        "kill_switch_active": kill_active,
        "p2_actual_validated": (
            status["actual_validation"]["p2"].get("validated")
            is True
        ),
        "p3_actual_validated": (
            status["actual_validation"]["p3"].get("validated")
            is True
        ),
        "p4_actual_validated": (
            status["actual_validation"]["p4"].get("validated")
            is True
        ),
        "paper_complete": False,
        "live_complete": False,
    }

    logger = JsonEventLogger(
        root / "release/operations_bundle/actual/"
               "operations_events.jsonl"
    )
    logger.write(
        "MONITOR_SNAPSHOT",
        level="ERROR" if alerts else "INFO",
        component="monitor",
        payload=result,
    )
    return result
