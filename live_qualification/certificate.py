from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def write_preparation_certificate(
    path: Path,
    *,
    qualification_result: dict[str, Any],
) -> dict[str, Any]:
    value = {
        "stage": "L6_PREPARATION_CERTIFICATE",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "offline_preparation_qualified": (
            qualification_result.get("qualified") is True
        ),
        "actual_live_long_run_qualified": False,
        "live_complete": False,
        "production_release_allowed": False,
        "automatic_order_replay_enabled": False,
        "actual_live_orders_submitted": 0,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return value
