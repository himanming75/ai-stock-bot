from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def write_shutdown_marker(
    root: Path,
    *,
    runtime_id: str,
    reason: str,
    last_cycle_number: int,
) -> dict[str, Any]:
    value = {
        "stage": "O4_GRACEFUL_SHUTDOWN",
        "runtime_id": runtime_id,
        "reason": reason,
        "last_cycle_number": last_cycle_number,
        "shutdown_at": datetime.now(timezone.utc).isoformat(),
        "state": "SHUTDOWN_MARKED",
        "new_order_submission_allowed": False,
        "automatic_order_replay_enabled": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }
    path = (
        root / "release/o4_runtime_resume_session_reporting/actual/"
               "graceful_shutdown_marker.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return value
