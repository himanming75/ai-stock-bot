from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from paper_web_ops.io import load_json,write_json

DEFAULT={
    "real_paper_read_enabled":True,
    "real_paper_shadow_enabled":True,
    "paper_submission_enabled":False,
    "maximum_orders_per_web_cycle":1,
    "paper_only":True,
    "live_submission_enabled":False,
}

def path(root:Path)->Path:
    return root/"release/v151_01_to_v155_64/config/paper_web_operations.json"

def load(root:Path)->dict[str,Any]:
    value=load_json(path(root))
    if not value:
        value={**DEFAULT,"updated_at":datetime.now(timezone.utc).isoformat()}
        write_json(path(root),value)
    return value

def validate(value:dict[str,Any])->dict[str,Any]:
    errors=[]
    if value.get("paper_only") is not True:
        errors.append("Paper-only mode must remain enabled.")
    if value.get("live_submission_enabled") is not False:
        errors.append("Live submission must remain disabled.")
    try:
        maximum=int(value.get("maximum_orders_per_web_cycle",0))
    except Exception:
        maximum=0
    if maximum != 1:
        errors.append("Web Paper cycle is limited to exactly one order.")
    normalized={
        "real_paper_read_enabled":bool(value.get("real_paper_read_enabled",True)),
        "real_paper_shadow_enabled":bool(value.get("real_paper_shadow_enabled",True)),
        "paper_submission_enabled":bool(value.get("paper_submission_enabled",False)),
        "maximum_orders_per_web_cycle":1,
        "paper_only":True,
        "live_submission_enabled":False,
    }
    return {"valid":not errors,"errors":errors,"normalized":normalized}

def save(root:Path,value:dict[str,Any])->dict[str,Any]:
    result=validate(value)
    if not result["valid"]:
        return {"ok":False,**result}
    normalized=result["normalized"]
    normalized["updated_at"]=datetime.now(timezone.utc).isoformat()
    write_json(path(root),normalized)
    return {"ok":True,"settings":normalized}
