from __future__ import annotations
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from paper_qualification.io import load_json,write_json

DEFAULT={
    "minimum_trading_days":20,
    "minimum_closed_trades":20,
    "minimum_win_rate_pct":45.0,
    "minimum_profit_factor":1.10,
    "minimum_sharpe":0.50,
    "maximum_drawdown_pct":10.0,
    "maximum_reconciliation_errors":0,
    "maximum_duplicate_orders":0,
    "maximum_critical_errors":0,
    "minimum_strategy_score":60.0,
    "paper_only":True,
    "live_submission_enabled":False,
}

def path(root:Path)->Path:
    return root/"release/v161_01_to_v165_64/config/paper_qualification_policy.json"

def load(root:Path)->dict[str,Any]:
    value=load_json(path(root))
    if not value:
        value=deepcopy(DEFAULT)
        value["updated_at"]=datetime.now(timezone.utc).isoformat()
        write_json(path(root),value)
    return value

def validate(value:dict[str,Any])->dict[str,Any]:
    errors=[]
    numeric={
        "minimum_trading_days":(1,365),
        "minimum_closed_trades":(1,100000),
        "minimum_win_rate_pct":(0,100),
        "minimum_profit_factor":(0,100),
        "minimum_sharpe":(-10,20),
        "maximum_drawdown_pct":(0,100),
        "maximum_reconciliation_errors":(0,100000),
        "maximum_duplicate_orders":(0,100000),
        "maximum_critical_errors":(0,100000),
        "minimum_strategy_score":(0,100),
    }
    normalized=deepcopy(DEFAULT)
    for key,(low,high) in numeric.items():
        try: number=float(value.get(key,DEFAULT[key]))
        except Exception: number=low-1
        if not low<=number<=high: errors.append(f"{key} must be between {low} and {high}.")
        normalized[key]=int(number) if isinstance(DEFAULT[key],int) else number
    if value.get("paper_only") is not True: errors.append("Paper-only must remain enabled.")
    if value.get("live_submission_enabled") is not False: errors.append("Live submission must remain disabled.")
    normalized["paper_only"]=True
    normalized["live_submission_enabled"]=False
    return {"valid":not errors,"errors":errors,"normalized":normalized}
