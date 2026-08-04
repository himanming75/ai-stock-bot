from __future__ import annotations
from typing import Any

def simulate(payload:dict[str,Any],policy:dict[str,Any])->dict[str,Any]:
    price=float(policy.get("simulated_fill_price",100.0))
    qty=float(payload.get("qty",0))
    return {
        "broker_request_simulated":True,
        "broker_response_simulated":True,
        "simulated_order_id":"SIM-"+str(payload.get("client_order_id")),
        "simulated_status":"filled",
        "simulated_fill_quantity":qty,
        "simulated_fill_price":price,
        "simulated_fill_notional":round(qty*price,2),
        "position_after_simulation":{
            "symbol":payload.get("symbol"),
            "quantity":qty if payload.get("side")=="buy" else -qty,
        },
        "actual_broker_request_sent":False,
        "actual_live_order_submitted":False,
    }
