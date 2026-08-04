from __future__ import annotations
from pathlib import Path
from typing import Any
from operations_manager.state import build
from operations_manager.config import save
from operations_manager.jobs import run
from operations_manager.recovery import create_plan
from web_controller.state import get_emergency

def get_payload(root:Path)->dict[str,Any]:
    return build(root)

def save_payload(root:Path,body:dict[str,Any])->dict[str,Any]:
    if get_emergency(root).get("enabled") is False and body.get("restart_on_failure") is True:
        # Restart changes are allowed only while stopped.
        return {"ok":False,"error":"ENABLE_EMERGENCY_STOP_BEFORE_RESTART_SETTING"}
    return save(root,body)

def run_payload(root:Path,body:dict[str,Any])->dict[str,Any]:
    job=str(body.get("job",""))
    if job in {"intraday_shadow","pre_market"} and get_emergency(root).get("enabled"):
        return {"ok":False,"error":"EMERGENCY_STOP_ENABLED","job":job}
    return run(root,job)

def recovery_payload(root:Path)->dict[str,Any]:
    return {"ok":True,"recovery":create_plan(root)}
