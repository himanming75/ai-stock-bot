from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from multi_day_scheduler.io import load_json,write_json,digest

def save_checkpoint(
    path: Path,
    scheduler_id: str,
    queue: dict[str, Any],
) -> dict[str, Any]:
    previous=load_json(path)
    generation=int(previous.get("generation",0))+1
    body={
        "scheduler_id":scheduler_id,
        "generation":generation,
        "updated_at":datetime.now(timezone.utc).isoformat(),
        "queue":queue,
        "previous_checkpoint_hash":previous.get("checkpoint_hash"),
    }
    body["checkpoint_hash"]=digest(body)
    write_json(path,body)
    return body

def resume_checkpoint(path: Path) -> dict[str, Any]:
    value=load_json(path)
    return {
        "resumable":bool(value),
        "generation":value.get("generation"),
        "scheduler_id":value.get("scheduler_id"),
        "queue":value.get("queue",{}),
    }
