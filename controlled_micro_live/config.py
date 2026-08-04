from __future__ import annotations
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from controlled_micro_live.io import load_json,write_json

DEFAULT={
    "maximum_quantity":1,
    "maximum_order_notional":100.0,
    "maximum_daily_orders":1,
    "maximum_daily_loss":20.0,
    "approval_token_expiry_minutes":5,
    "manual_approval_required":True,
    "qualification_required":True,
    "kill_switch_required_clear":True,
    "dry_run_only":True,
    "live_network_enabled":False,
    "live_write_enabled":False,
    "live_submission_enabled":False,
}

def path(root:Path)->Path:
    return root/"release/v171_01_to_v175_64/config/controlled_micro_live_policy.json"

def load(root:Path)->dict[str,Any]:
    value=load_json(path(root))
    if not value:
        value=deepcopy(DEFAULT)
        value["updated_at"]=datetime.now(timezone.utc).isoformat()
        write_json(path(root),value)
    return value

def validate(value:dict[str,Any])->dict[str,Any]:
    errors=[]
    if int(value.get("maximum_quantity",0)) != 1:
        errors.append("maximum_quantity must remain exactly 1.")
    if float(value.get("maximum_order_notional",0)) > 100:
        errors.append("maximum_order_notional cannot exceed $100.")
    if int(value.get("maximum_daily_orders",0)) != 1:
        errors.append("maximum_daily_orders must remain exactly 1.")
    if value.get("dry_run_only") is not True:
        errors.append("dry_run_only must remain enabled.")
    for key in ("live_network_enabled","live_write_enabled","live_submission_enabled"):
        if value.get(key) is not False:
            errors.append(f"{key} must remain disabled.")
    normalized=deepcopy(DEFAULT)
    normalized.update(value)
    normalized["maximum_quantity"]=1
    normalized["maximum_order_notional"]=min(float(value.get("maximum_order_notional",100)),100.0)
    normalized["maximum_daily_orders"]=1
    normalized["dry_run_only"]=True
    normalized["live_network_enabled"]=False
    normalized["live_write_enabled"]=False
    normalized["live_submission_enabled"]=False
    return {"valid":not errors,"errors":errors,"normalized":normalized}
