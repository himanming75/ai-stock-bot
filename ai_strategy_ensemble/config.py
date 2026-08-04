from __future__ import annotations
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from ai_strategy_ensemble.io import load_json,write_json

DEFAULT={
 "minimum_observations":10,
 "minimum_score":55.0,
 "champion_minimum_score":70.0,
 "maximum_strategy_weight_pct":60.0,
 "minimum_strategy_weight_pct":5.0,
 "maximum_active_strategies":3,
 "drawdown_penalty_factor":2.0,
 "loss_penalty_factor":1.0,
 "risk_gate_required":True,
 "automatic_strategy_promotion_enabled":False,
 "automatic_order_submission_enabled":False,
 "broker_write_enabled":False,
 "live_submission_enabled":False
}

def path(root:Path)->Path:
    return root/"release/v211_01_to_v215_64/config/ai_strategy_ensemble_policy.json"

def load(root:Path)->dict[str,Any]:
    value=load_json(path(root))
    if not value:
        value=deepcopy(DEFAULT)
        value["updated_at"]=datetime.now(timezone.utc).isoformat()
        write_json(path(root),value)
    return value

def validate(value:dict[str,Any])->dict[str,Any]:
    errors=[]
    for key in ("automatic_strategy_promotion_enabled","automatic_order_submission_enabled","broker_write_enabled","live_submission_enabled"):
        if value.get(key) is not False:
            errors.append(f"{key} must remain disabled.")
    try:
        max_active=int(value.get("maximum_active_strategies",0))
    except Exception:
        max_active=0
    if not 1<=max_active<=10:
        errors.append("maximum_active_strategies must be 1-10.")
    normalized=deepcopy(DEFAULT)
    normalized.update(value)
    normalized["maximum_active_strategies"]=max_active or 3
    normalized["automatic_strategy_promotion_enabled"]=False
    normalized["automatic_order_submission_enabled"]=False
    normalized["broker_write_enabled"]=False
    normalized["live_submission_enabled"]=False
    return {"valid":not errors,"errors":errors,"normalized":normalized}
