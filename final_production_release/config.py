from __future__ import annotations
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from final_production_release.io import load_json,write_json

DEFAULT={
 "release_name":"AI_STOCK_BOT_V220_FINAL_PRODUCTION",
 "base_commit":"46c700805ea5e167cab01bf564ba162d435f9588",
 "required_stage_count":16,
 "require_web_controller":True,
 "require_rollback_script":True,
 "require_operator_guide":True,
 "require_all_live_orders_zero":True,
 "automatic_strategy_promotion_enabled":False,
 "automatic_order_submission_enabled":False,
 "broker_write_enabled":False,
 "live_submission_enabled":False,
 "live_network_write_enabled":False
}

def path(root:Path)->Path:
    return root/"release/v216_01_to_v220_64/config/final_production_release_policy.json"

def load(root:Path)->dict[str,Any]:
    value=load_json(path(root))
    if not value:
        value=deepcopy(DEFAULT)
        value["updated_at"]=datetime.now(timezone.utc).isoformat()
        write_json(path(root),value)
    return value

def validate(value:dict[str,Any])->dict[str,Any]:
    errors=[]
    normalized=deepcopy(DEFAULT)
    normalized.update(value)
    for key in (
      "automatic_strategy_promotion_enabled","automatic_order_submission_enabled",
      "broker_write_enabled","live_submission_enabled","live_network_write_enabled"
    ):
        if value.get(key) is not False:
            errors.append(f"{key} must remain disabled.")
        normalized[key]=False
    try: count=int(value.get("required_stage_count",0))
    except Exception: count=0
    if count<10:errors.append("required_stage_count must be at least 10.")
    normalized["required_stage_count"]=count or DEFAULT["required_stage_count"]
    return {"valid":not errors,"errors":errors,"normalized":normalized}
