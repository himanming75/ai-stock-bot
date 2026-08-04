from __future__ import annotations
from pathlib import Path
from typing import Any
from paper_web_ops.state import build
from paper_web_ops.runner import execute
from paper_web_ops.settings import save
from web_controller.state import get_emergency

def get_payload(root:Path)->dict[str,Any]:
    return build(root)

def run_payload(root:Path,body:dict[str,Any])->dict[str,Any]:
    return execute(
        root,
        str(body.get("action","")),
        str(body.get("confirmation","")),
    )

def save_settings_payload(root:Path,body:dict[str,Any])->dict[str,Any]:
    if get_emergency(root).get("enabled"):
        return {"ok":False,"error":"EMERGENCY_STOP_ENABLED"}
    return save(root,body)
