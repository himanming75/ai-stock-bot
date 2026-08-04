from __future__ import annotations
from typing import Any
from autonomous_orchestrator.io import digest

def build(cycle_id:str,state:str,positions:list[dict[str,Any]],previous:dict[str,Any])->dict[str,Any]:
    body={
        "cycle_id":cycle_id,
        "state":state,
        "generation":int(previous.get("generation",0))+1,
        "previous_checkpoint_hash":previous.get("checkpoint_hash"),
        "positions":positions,
    }
    body["checkpoint_hash"]=digest(body)
    return body
