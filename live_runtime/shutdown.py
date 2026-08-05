from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path


def write_live_shutdown_marker(
    path: Path,
    *,
    runtime_id: str,
    last_cycle_number: int,
    reason: str,
) -> dict:
    value = {
        "stage": "L5_GRACEFUL_SHUTDOWN",
        "runtime_id": runtime_id,
        "last_cycle_number": last_cycle_number,
        "reason": reason,
        "shutdown_at": datetime.now(timezone.utc).isoformat(),
        "new_live_order_submission_allowed": False,
        "automatic_order_replay_enabled": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return value
