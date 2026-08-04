from __future__ import annotations
from typing import Any
from broker_safe_execution.io import digest

def build_order_intents(
    account_equity: float,
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    intents=[]
    for row in policy.get("sample_order_intents",[]):
        symbol=str(row.get("symbol","")).upper()
        side=str(row.get("side","BUY")).upper()
        quantity=float(row.get("quantity",0.0))
        limit_price=row.get("limit_price")
        intent={
            "intent_id":digest({
                "symbol":symbol,
                "side":side,
                "quantity":quantity,
                "limit_price":limit_price,
                "account_equity":account_equity,
            })[:24],
            "symbol":symbol,
            "side":side,
            "quantity":quantity,
            "order_type":str(row.get("order_type","MARKET")).upper(),
            "time_in_force":str(row.get("time_in_force","DAY")).upper(),
            "limit_price":limit_price,
            "estimated_notional":round(
                quantity*float(limit_price or row.get("reference_price",0.0)),
                2,
            ),
            "source":"SAFE_EXECUTION_FIXTURE",
            "state":"CREATED",
        }
        intents.append(intent)
    return intents
