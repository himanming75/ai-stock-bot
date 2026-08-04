from __future__ import annotations
from datetime import datetime,timezone
from copy import deepcopy
from pathlib import Path
from typing import Any
from strategy_manager.io import load_json,write_json

DEFAULT={
    "strategies":{
        "momentum":{"enabled":True,"weight_pct":50.0},
        "mean_reversion":{"enabled":False,"weight_pct":25.0},
        "breakout":{"enabled":False,"weight_pct":25.0},
    },
    "symbols":["AAPL","MSFT","SPY"],
    "risk":{
        "maximum_order_notional":250.0,
        "maximum_quantity":1,
        "maximum_daily_orders":3,
        "maximum_daily_loss":50.0,
        "maximum_positions":3,
    },
    "paper_only":True,
    "live_submission_enabled":False,
}

def path(root:Path)->Path:
    return root/"release/v146_01_to_v150_64/config/strategy_manager.json"

def backup_path(root:Path)->Path:
    return root/"release/v146_01_to_v150_64/config/strategy_manager.backup.json"

def load(root:Path)->dict[str,Any]:
    value=load_json(path(root))
    if not value:
        value=deepcopy(DEFAULT)
        value["updated_at"]=datetime.now(timezone.utc).isoformat()
        write_json(path(root),value)
    return value

def validate(value:dict[str,Any])->dict[str,Any]:
    errors=[]
    symbols=value.get("symbols",[])
    if not isinstance(symbols,list) or not symbols:
        errors.append("At least one symbol is required.")
    if len(symbols)>20:
        errors.append("Maximum 20 symbols.")
    cleaned=[]
    for symbol in symbols if isinstance(symbols,list) else []:
        s=str(symbol).strip().upper()
        if not s or not s.replace(".","").replace("-","").isalnum():
            errors.append(f"Invalid symbol: {symbol}")
        elif s not in cleaned:
            cleaned.append(s)
    strategies=value.get("strategies",{})
    if not isinstance(strategies,dict) or not strategies:
        errors.append("Strategies are required.")
    enabled=sum(1 for v in strategies.values() if isinstance(v,dict) and v.get("enabled"))
    if enabled<1:
        errors.append("At least one strategy must be enabled.")
    risk=value.get("risk",{})
    limits={
        "maximum_order_notional":(1,10000),
        "maximum_quantity":(1,1000),
        "maximum_daily_orders":(1,1000),
        "maximum_daily_loss":(1,100000),
        "maximum_positions":(1,100),
    }
    for key,(low,high) in limits.items():
        try: number=float(risk.get(key,0))
        except Exception: number=0
        if not low<=number<=high:
            errors.append(f"{key} must be between {low} and {high}.")
    if value.get("live_submission_enabled") is not False:
        errors.append("Live submission must remain disabled.")
    if value.get("paper_only") is not True:
        errors.append("Paper-only mode must remain enabled.")
    normalized={
        "strategies":strategies,
        "symbols":cleaned,
        "risk":{
            "maximum_order_notional":float(risk.get("maximum_order_notional",250)),
            "maximum_quantity":int(float(risk.get("maximum_quantity",1))),
            "maximum_daily_orders":int(float(risk.get("maximum_daily_orders",3))),
            "maximum_daily_loss":float(risk.get("maximum_daily_loss",50)),
            "maximum_positions":int(float(risk.get("maximum_positions",3))),
        },
        "paper_only":True,
        "live_submission_enabled":False,
    }
    return {"valid":not errors,"errors":errors,"normalized":normalized}

def save(root:Path,value:dict[str,Any])->dict[str,Any]:
    result=validate(value)
    if not result["valid"]:
        return {"ok":False,**result}
    current=load(root)
    write_json(backup_path(root),current)
    normalized=result["normalized"]
    normalized["updated_at"]=datetime.now(timezone.utc).isoformat()
    write_json(path(root),normalized)
    return {"ok":True,"config":normalized,"errors":[]}

def restore(root:Path)->dict[str,Any]:
    backup=load_json(backup_path(root))
    if not backup:
        return {"ok":False,"error":"BACKUP_NOT_FOUND"}
    result=validate(backup)
    if not result["valid"]:
        return {"ok":False,"error":"BACKUP_INVALID","errors":result["errors"]}
    backup["updated_at"]=datetime.now(timezone.utc).isoformat()
    write_json(path(root),backup)
    return {"ok":True,"config":backup}
