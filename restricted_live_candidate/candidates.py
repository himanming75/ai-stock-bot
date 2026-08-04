from __future__ import annotations
from typing import Any

def build(source:dict[str,Any])->list[dict[str,Any]]:
    rows=[]
    for c in source.get("live_order_candidates",[]):
        rows.append({
            "candidate_id":c.get("candidate_id"),
            "symbol":c.get("symbol"),
            "side":c.get("side"),
            "quantity":float(c.get("quantity",0)),
            "order_type":c.get("order_type"),
            "estimated_notional":float(c.get("estimated_notional",0)),
            "restricted_live_candidate":True,
            "live_order_submitted":False,
        })
    return rows
