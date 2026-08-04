from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from final_system_integration.io import load_json,write_json,digest

def save_checkpoint(
    path: Path,
    integration_id: str,
    readiness: dict[str, Any],
    pipeline: dict[str, Any],
) -> dict[str, Any]:
    previous=load_json(path)
    generation=int(previous.get("generation",0))+1
    body={
        "integration_id":integration_id,
        "generation":generation,
        "updated_at":datetime.now(timezone.utc).isoformat(),
        "readiness_score":readiness.get("readiness_score"),
        "readiness_level":readiness.get("readiness_level"),
        "pipeline_ready_steps":pipeline.get("ready_steps"),
        "pipeline_total_steps":pipeline.get("total_steps"),
        "previous_checkpoint_hash":previous.get("checkpoint_hash"),
    }
    body["checkpoint_hash"]=digest(body)
    write_json(path,body)
    return body
