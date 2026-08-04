from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from continuous_service_runtime.io import load_json, write_json, digest

def save_checkpoint(
    path: Path,
    runtime_id: str,
    state: str,
    tick_count: int,
    heartbeat_count: int,
) -> dict[str, Any]:
    previous = load_json(path)
    generation = int(previous.get("generation", 0)) + 1
    body = {
        "runtime_id": runtime_id,
        "state": state,
        "tick_count": tick_count,
        "heartbeat_count": heartbeat_count,
        "generation": generation,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "previous_checkpoint_hash": previous.get("checkpoint_hash"),
    }
    body["checkpoint_hash"] = digest(body)
    write_json(path, body)
    return body
