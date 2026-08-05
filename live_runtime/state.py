from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_heartbeat(
    path: Path,
    *,
    runtime_id: str,
    cycle_number: int,
    state: str,
) -> dict[str, Any]:
    value = {
        "runtime_id": runtime_id,
        "cycle_number": cycle_number,
        "state": state,
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(path, value)
    return value


def write_checkpoint(
    path: Path,
    *,
    runtime_id: str,
    cycle_id: str,
    cycle_number: int,
    state: str,
) -> dict[str, Any]:
    value = {
        "stage": "L5",
        "runtime_id": runtime_id,
        "cycle_id": cycle_id,
        "cycle_number": cycle_number,
        "state": state,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "automatic_order_replay_enabled": False,
    }
    write_json(path, value)
    return value
