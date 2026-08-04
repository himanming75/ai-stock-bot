from __future__ import annotations
from typing import Any

def simulate_fill_sync(
    queue: dict[str, Any],
) -> dict[str, Any]:
    rows=[]
    for item in queue.get("rows",[]):
        rows.append({
            "intent_id":item.get("intent_id"),
            "symbol":item.get("symbol"),
            "broker_order_id":None,
            "status":"NOT_SUBMITTED",
            "filled_quantity":0.0,
            "average_fill_price":None,
            "source":"SAFE_LOCAL_SYNC",
        })
    return {
        "order_sync_count":len(rows),
        "orders":rows,
        "real_broker_sync_performed":False,
    }

def simulate_position_sync() -> dict[str, Any]:
    return {
        "position_sync_count":0,
        "positions":[],
        "real_broker_sync_performed":False,
    }

def simulate_cancel_replace(queue: dict[str, Any]) -> dict[str, Any]:
    return {
        "cancel_candidates":sum(
            1 for row in queue.get("rows",[])
            if row.get("state")=="WAITING_FOR_MANUAL_APPROVAL"
        ),
        "replace_candidates":0,
        "cancel_requests_executed":0,
        "replace_requests_executed":0,
        "simulation_only":True,
    }
