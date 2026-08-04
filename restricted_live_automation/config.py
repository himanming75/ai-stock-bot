from __future__ import annotations
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from restricted_live_automation.io import load_json,write_json

DEFAULT={
 "allowed_symbols":["AAPL","MSFT","SPY"],
 "allowed_strategies":["momentum"],
 "trading_start":"09:35",
 "new_order_cutoff":"15:30",
 "maximum_quantity":1,
 "maximum_order_notional":100.0,
 "maximum_daily_orders":1,
 "maximum_daily_loss":20.0,
 "maximum_open_positions":1,
 "maximum_gross_exposure":100.0,
 "qualification_required":True,
 "micro_live_dry_run_required":True,
 "approval_token_required":True,
 "kill_switch_required_clear":True,
 "automatic_submission_enabled":False,
 "live_network_enabled":False,
 "live_write_enabled":False,
 "live_submission_enabled":False
}

def path(root:Path)->Path:
    return root/"release/v176_01_to_v180_64/config/restricted_live_automation_policy.json"

def load(root:Path)->dict[str,Any]:
    value=load_json(path(root))
    if not value:
        value=deepcopy(DEFAULT)
        value["updated_at"]=datetime.now(timezone.utc).isoformat()
        write_json(path(root),value)
    return value

def validate(value:dict[str,Any])->dict[str,Any]:
    errors=[]
    if not isinstance(value.get("allowed_symbols"),list) or not value.get("allowed_symbols"):
        errors.append("allowed_symbols required.")
    if not isinstance(value.get("allowed_strategies"),list) or not value.get("allowed_strategies"):
        errors.append("allowed_strategies required.")
    if int(value.get("maximum_quantity",0)) != 1:
        errors.append("maximum_quantity must be exactly 1.")
    if float(value.get("maximum_order_notional",0)) > 100:
        errors.append("maximum_order_notional cannot exceed 100.")
    if int(value.get("maximum_daily_orders",0)) != 1:
        errors.append("maximum_daily_orders must be exactly 1.")
    for key in ("automatic_submission_enabled","live_network_enabled","live_write_enabled","live_submission_enabled"):
        if value.get(key) is not False:
            errors.append(f"{key} must remain disabled.")
    normalized=deepcopy(DEFAULT)
    normalized.update(value)
    normalized["maximum_quantity"]=1
    normalized["maximum_order_notional"]=min(float(value.get("maximum_order_notional",100)),100.0)
    normalized["maximum_daily_orders"]=1
    normalized["automatic_submission_enabled"]=False
    normalized["live_network_enabled"]=False
    normalized["live_write_enabled"]=False
    normalized["live_submission_enabled"]=False
    return {"valid":not errors,"errors":errors,"normalized":normalized}
