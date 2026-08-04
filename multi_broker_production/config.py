from __future__ import annotations
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from multi_broker_production.io import load_json,write_json

DEFAULT={
 "maximum_brokers":5,
 "maximum_accounts":10,
 "maximum_positions":50,
 "maximum_broker_weight_pct":80.0,
 "minimum_healthy_brokers":1,
 "maximum_read_latency_ms":3000,
 "failover_enabled":True,
 "automatic_failover_write_enabled":False,
 "broker_write_enabled":False,
 "live_submission_enabled":False
}

def path(root:Path)->Path:
    return root/"release/v196_01_to_v200_64/config/multi_broker_policy.json"

def load(root:Path)->dict[str,Any]:
    value=load_json(path(root))
    if not value:
        value=deepcopy(DEFAULT)
        value["updated_at"]=datetime.now(timezone.utc).isoformat()
        write_json(path(root),value)
    return value

def validate(value:dict[str,Any])->dict[str,Any]:
    errors=[]
    for key in ("automatic_failover_write_enabled","broker_write_enabled","live_submission_enabled"):
        if value.get(key) is not False:
            errors.append(f"{key} must remain disabled.")
    try:
        max_brokers=int(value.get("maximum_brokers",0))
        max_accounts=int(value.get("maximum_accounts",0))
    except Exception:
        max_brokers=max_accounts=0
    if not 1<=max_brokers<=20: errors.append("maximum_brokers must be 1-20.")
    if not 1<=max_accounts<=100: errors.append("maximum_accounts must be 1-100.")
    normalized=deepcopy(DEFAULT)
    normalized.update(value)
    normalized["maximum_brokers"]=max_brokers or 5
    normalized["maximum_accounts"]=max_accounts or 10
    normalized["automatic_failover_write_enabled"]=False
    normalized["broker_write_enabled"]=False
    normalized["live_submission_enabled"]=False
    return {"valid":not errors,"errors":errors,"normalized":normalized}
