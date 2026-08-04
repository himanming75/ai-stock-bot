from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from fast_track_paper.io import load_json,write_json,digest

def save_checkpoint(
    path: Path,
    cycle_id: str,
    state: str,
    positions: list[dict[str, Any]],
    close_result: dict[str, Any],
) -> dict[str, Any]:
    previous=load_json(path)
    generation=int(previous.get("generation",0))+1
    body={
        "cycle_id":cycle_id,
        "state":state,
        "positions":positions,
        "close_result":close_result,
        "generation":generation,
        "updated_at":datetime.now(timezone.utc).isoformat(),
        "previous_checkpoint_hash":previous.get("checkpoint_hash"),
    }
    body["checkpoint_hash"]=digest(body)
    write_json(path,body)
    return body
