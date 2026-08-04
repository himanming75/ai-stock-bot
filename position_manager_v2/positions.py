from __future__ import annotations
from typing import Any

def apply_buy(position: dict[str, Any], quantity: float, price: float) -> dict[str, Any]:
    old_qty = float(position.get("quantity", 0) or 0)
    old_avg = float(position.get("average_cost", 0) or 0)
    qty = float(quantity)
    new_qty = old_qty + qty
    new_avg = ((old_qty * old_avg) + (qty * float(price))) / new_qty if new_qty else 0
    return {**position, "quantity": new_qty, "average_cost": round(new_avg, 6)}

def apply_sell(position: dict[str, Any], quantity: float, price: float) -> dict[str, Any]:
    old_qty = float(position.get("quantity", 0) or 0)
    qty = float(quantity)
    if qty > old_qty:
        raise ValueError("Sell quantity exceeds position.")
    average = float(position.get("average_cost", 0) or 0)
    realized = float(position.get("realized_pnl", 0) or 0) + (float(price) - average) * qty
    new_qty = old_qty - qty
    return {
        **position,
        "quantity": new_qty,
        "average_cost": average if new_qty else 0.0,
        "realized_pnl": round(realized, 6),
    }

def mark(position: dict[str, Any], market_price: float) -> dict[str, Any]:
    qty = float(position.get("quantity", 0) or 0)
    average = float(position.get("average_cost", 0) or 0)
    market = float(market_price)
    market_value = qty * market
    unrealized = (market - average) * qty
    return {
        **position,
        "market_price": market,
        "market_value": round(market_value, 2),
        "unrealized_pnl": round(unrealized, 2),
        "total_pnl": round(unrealized + float(position.get("realized_pnl", 0) or 0), 2),
    }
