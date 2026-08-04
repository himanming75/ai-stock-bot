from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from master_ai_orchestrator.io import load_json, write_json, digest

def build_checkpoint(
    root: Path,
    orchestration_id: str,
    workflow: dict[str, Any],
) -> dict[str, Any]:
    path = (
        root / "release/v102_01_to_v102_32/actual/"
        "master_orchestrator_checkpoint.json"
    )
    previous = load_json(path)
    generation = int(previous.get("generation", 0)) + 1
    body = {
        "orchestration_id": orchestration_id,
        "generation": generation,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "ready_step_count": workflow.get("ready_step_count", 0),
        "blocked_step_count": workflow.get("blocked_step_count", 0),
        "workflow_passed": workflow.get("passed", False),
        "previous_checkpoint_hash": previous.get("checkpoint_hash"),
    }
    body["checkpoint_hash"] = digest(body)
    write_json(path, body)
    return body
