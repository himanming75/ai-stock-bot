from __future__ import annotations
from typing import Any

def simulate(plans:list[dict[str,Any]],market_open:bool,policy:dict[str,Any])->dict[str,Any]:
    allowed=(
        market_open
        and policy.get("paper_execution_enabled") is True
        and policy.get("live_submission_enabled") is False
    )
    fills=[]
    if allowed:
        for p in plans[:int(policy.get("maximum_paper_orders_per_cycle",1))]:
            fills.append({
                "order_id":"PAPER-SIM-"+str(p.get("client_order_id")),
                "symbol":p.get("symbol"),
                "side":p.get("side"),
                "qty":float(p.get("qty",0)),
                "fill_price":float(p.get("estimated_price",0)),
                "status":"filled",
                "paper_only":True,
            })
    return {
        "paper_execution_authorized":allowed and bool(plans),
        "paper_orders_submitted":len(fills),
        "paper_fills":fills,
        "actual_live_orders_submitted":0,
        "live_submission_attempted":False,
    }
