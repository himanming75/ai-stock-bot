from __future__ import annotations
from typing import Any

def build_payload(candidate:dict[str,Any])->dict[str,Any]:
    return {
        "symbol":candidate.get("symbol"),
        "side":candidate.get("side"),
        "qty":str(int(float(candidate.get("quantity",0)))),
        "type":candidate.get("order_type","market"),
        "time_in_force":"day",
        "client_order_id":"review-"+str(candidate.get("candidate_id")),
        "review_only":True,
        "submitted":False,
    }
