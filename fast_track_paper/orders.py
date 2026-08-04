from __future__ import annotations
from typing import Any
from fast_track_paper.io import digest

def build_orders(
    daily_plan: dict[str, Any],
    account_equity: float,
    reference_prices: dict[str, float],
    symbol_map: dict[str, str],
) -> list[dict[str, Any]]:
    orders=[]
    for row in daily_plan.get("plans",[]):
        if row.get("state")!="AUTHORIZED_FOR_PAPER_SIMULATION":
            continue
        strategy_id=str(row.get("strategy_id"))
        symbol=symbol_map.get(strategy_id,"SPY")
        price=float(reference_prices.get(symbol,100.0))
        target_weight=float(row.get("target_weight_pct",0.0))/100.0
        notional=round(account_equity*target_weight,2)
        quantity=max(0,int(notional//price))
        order={
            "paper_order_id":digest({
                "plan_key":row.get("plan_key"),
                "symbol":symbol,
                "quantity":quantity,
                "price":price,
            })[:24],
            "plan_key":row.get("plan_key"),
            "strategy_id":strategy_id,
            "symbol":symbol,
            "side":"BUY",
            "order_type":"MARKET",
            "requested_quantity":quantity,
            "reference_price":price,
            "planned_notional":round(quantity*price,2),
            "state":"PAPER_ORDER_CREATED" if quantity>0 else "PAPER_ORDER_SKIPPED",
            "actual_broker_submission":False,
        }
        orders.append(order)
    return orders
