from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from autonomous_cycle.io import load_json, write_json, digest

def save_checkpoint(
    path: Path,
    cycle: dict[str, Any],
) -> dict[str, Any]:
    previous = load_json(path)
    generation = int(previous.get("generation", 0)) + 1
    body = {
        "cycle_id": cycle.get("cycle_id"),
        "cycle_key": cycle.get("cycle_key"),
        "state": cycle.get("state"),
        "current_step": cycle.get("current_step"),
        "steps": cycle.get("steps", []),
        "generation": generation,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "previous_checkpoint_hash": previous.get("checkpoint_hash"),
    }
    body["checkpoint_hash"] = digest(body)
    write_json(path, body)
    return body

def resume_checkpoint(path: Path, cycle_id: str) -> dict[str, Any]:
    checkpoint = load_json(path)
    if checkpoint.get("cycle_id") != cycle_id:
        return {"resumable": False, "reason": "CHECKPOINT_NOT_FOUND"}
    return {
        "resumable": True,
        "generation": checkpoint.get("generation"),
        "state": checkpoint.get("state"),
        "current_step": checkpoint.get("current_step"),
        "steps": checkpoint.get("steps", []),
    }
