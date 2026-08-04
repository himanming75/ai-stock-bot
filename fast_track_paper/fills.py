from __future__ import annotations
from typing import Any
from fast_track_paper.io import digest

def fill_ratio(order_index: int, policy: dict[str, Any]) -> float:
    ratios=policy.get("deterministic_fill_ratios",[1.0,0.5,0.0])
    if not ratios:
        return 1.0
    return float(ratios[order_index % len(ratios)])

def simulate_fills(
    orders: list[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    fills=[]
    slippage_bps=float(policy.get("slippage_bps",5.0))
    for index,order in enumerate(orders):
        requested=int(order.get("requested_quantity",0))
        ratio=fill_ratio(index,policy)
        filled=int(math_floor(requested*ratio))
        price=float(order.get("reference_price",0.0))
        fill_price=round(price*(1+slippage_bps/10000.0),4) if filled else None
        if filled==0:
            state="NOT_FILLED"
        elif filled<requested:
            state="PARTIAL_FILL"
        else:
            state="FILLED"
        fills.append({
            "fill_id":digest({
                "order_id":order.get("paper_order_id"),
                "filled":filled,
                "fill_price":fill_price,
            })[:24],
            "paper_order_id":order.get("paper_order_id"),
            "strategy_id":order.get("strategy_id"),
            "symbol":order.get("symbol"),
            "requested_quantity":requested,
            "filled_quantity":filled,
            "remaining_quantity":requested-filled,
            "fill_price":fill_price,
            "fill_notional":round(filled*(fill_price or 0.0),2),
            "state":state,
            "actual_broker_submission":False,
        })
    return fills

def math_floor(value: float) -> int:
    return int(value//1)
