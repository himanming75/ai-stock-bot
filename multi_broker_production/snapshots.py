from __future__ import annotations
import time
from pathlib import Path
from typing import Any
from multi_broker_production.io import load_json
from multi_broker_production.registry import active_rows

def collect(root:Path)->list[dict[str,Any]]:
    rows=[]
    for entry in active_rows(root):
        started=time.perf_counter()
        fixture=load_json(root/entry["fixture_path"])
        latency_ms=round((time.perf_counter()-started)*1000,3)
        account=fixture.get("account",{})
        positions=fixture.get("positions",[])
        orders=fixture.get("orders",[])
        rows.append({
            "broker_id":entry["broker_id"],
            "account_id_masked":account.get("account_id_masked","NOT_AVAILABLE"),
            "mode":account.get("mode","READ_ONLY"),
            "status":account.get("status","UNKNOWN"),
            "cash":float(account.get("cash",0) or 0),
            "equity":float(account.get("equity",0) or 0),
            "buying_power":float(account.get("buying_power",0) or 0),
            "positions":positions,
            "orders":orders,
            "read_latency_ms":latency_ms,
            "read_only":True,
            "supports_orders":False,
            "actual_live_orders_submitted":0,
        })
    return rows
