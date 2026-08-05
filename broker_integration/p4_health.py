from __future__ import annotations
from pathlib import Path
import shutil
from typing import Any


def health_check(
    *,
    root: Path,
    kill_switch: dict[str, Any],
    market_clock: dict[str, Any],
    p2_actual_validated: bool,
    p3_actual_validated: bool,
    require_market_open: bool,
    require_p2_actual_validation: bool,
    require_p3_actual_validation: bool,
    minimum_free_bytes: int = 100_000_000,
) -> dict[str, Any]:
    free_bytes = shutil.disk_usage(root).free
    checks = {
        "kill_switch_inactive": (
            kill_switch.get("kill_switch_active") is False
        ),
        "market_condition": (
            not require_market_open
            or market_clock.get("is_open") is True
        ),
        "p2_actual_validation": (
            not require_p2_actual_validation
            or p2_actual_validated is True
        ),
        "p3_actual_validation": (
            not require_p3_actual_validation
            or p3_actual_validated is True
        ),
        "disk_space_sufficient": free_bytes >= minimum_free_bytes,
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "healthy": not failed,
        "checks": checks,
        "failed": failed,
        "free_disk_bytes": free_bytes,
        "minimum_free_bytes": minimum_free_bytes,
    }
