from __future__ import annotations
from pathlib import Path
from typing import Any
from strategy_manager.config import load,save,restore,validate
from strategy_manager.apply import build_runtime_policy
from web_controller.state import get_emergency

def get_payload(root:Path)->dict[str,Any]:
    return {
        "config":load(root),
        "runtime_policy":build_runtime_policy(root),
        "emergency_stop":get_emergency(root),
        "actual_live_orders_submitted":0,
    }

def update_payload(root:Path,body:dict[str,Any])->dict[str,Any]:
    if get_emergency(root).get("enabled"):
        return {"ok":False,"error":"EMERGENCY_STOP_ENABLED"}
    return save(root,body)

def validate_payload(body:dict[str,Any])->dict[str,Any]:
    return validate(body)

def restore_payload(root:Path)->dict[str,Any]:
    if get_emergency(root).get("enabled"):
        return {"ok":False,"error":"EMERGENCY_STOP_ENABLED"}
    return restore(root)
