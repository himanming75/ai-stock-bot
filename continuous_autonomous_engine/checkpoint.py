from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from continuous_autonomous_engine.io import load_json,write_json,digest

def save_checkpoint(
    path: Path,
    engine_id: str,
    selected_session: dict[str, Any],
    phases: list[dict[str, Any]],
    state: str,
) -> dict[str, Any]:
    previous=load_json(path)
    generation=int(previous.get("generation",0))+1
    body={
        "engine_id":engine_id,
        "generation":generation,
        "updated_at":datetime.now(timezone.utc).isoformat(),
        "state":state,
        "selected_session":selected_session,
        "phases":phases,
        "previous_checkpoint_hash":previous.get("checkpoint_hash"),
    }
    body["checkpoint_hash"]=digest(body)
    write_json(path,body)
    return body
