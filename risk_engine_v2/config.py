from __future__ import annotations
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from risk_engine_v2.io import load_json,write_json

DEFAULT={
 "maximum_drawdown_pct":10.0,
 "maximum_daily_loss_pct":2.0,
 "maximum_consecutive_losses":4,
 "circuit_breaker_minutes":30,
 "maximum_atr_pct":5.0,
 "maximum_symbol_weight_pct":20.0,
 "maximum_sector_weight_pct":40.0,
 "maximum_correlation":0.90,
 "risk_per_trade_pct":0.5,
 "maximum_position_notional":1000.0,
 "maximum_position_quantity":100,
 "kill_switch_default_on":True,
 "broker_write_enabled":False,
 "live_submission_enabled":False
}

def path(root:Path)->Path:
    return root/"release/v206_01_to_v210_64/config/risk_engine_v2_policy.json"

def load(root:Path)->dict[str,Any]:
    value=load_json(path(root))
    if not value:
        value=deepcopy(DEFAULT)
        value["updated_at"]=datetime.now(timezone.utc).isoformat()
        write_json(path(root),value)
    return value

def validate(value:dict[str,Any])->dict[str,Any]:
    errors=[]
    ranges={
      "maximum_drawdown_pct":(0.1,50),
      "maximum_daily_loss_pct":(0.1,20),
      "maximum_atr_pct":(0.1,50),
      "maximum_symbol_weight_pct":(1,100),
      "maximum_sector_weight_pct":(1,100),
      "maximum_correlation":(0,1),
      "risk_per_trade_pct":(0.01,5),
      "maximum_position_notional":(1,1000000),
      "maximum_position_quantity":(1,1000000),
    }
    normalized=deepcopy(DEFAULT)
    normalized.update(value)
    for key,(lo,hi) in ranges.items():
        try:number=float(value.get(key,DEFAULT[key]))
        except Exception:number=lo-1
        if not lo<=number<=hi:errors.append(f"{key} must be between {lo} and {hi}.")
        normalized[key]=int(number) if isinstance(DEFAULT[key],int) else number
    for key in ("broker_write_enabled","live_submission_enabled"):
        if value.get(key) is not False:errors.append(f"{key} must remain disabled.")
        normalized[key]=False
    return {"valid":not errors,"errors":errors,"normalized":normalized}
