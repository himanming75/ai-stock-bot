from __future__ import annotations
from typing import Any

def apply_fill(
    cash: float,
    positions: dict[str, dict[str, float]],
    plan: dict[str, Any],
    fill: dict[str, Any],
) -> tuple[float, dict[str, dict[str, float]]]:
    if fill.get("state") not in {"FILLED", "PARTIALLY_FILLED"}:
        return cash, positions

    symbol = str(plan.get("symbol"))
    side = str(plan.get("side", "BUY")).upper()
    quantity = float(fill.get("filled_quantity", 0.0))
    price = float(fill.get("fill_price", 0.0))
    commission = float(fill.get("commission", 0.0))
    current = dict(positions.get(symbol, {"quantity": 0.0, "average_cost": 0.0}))

    if side == "BUY":
        previous_qty = float(current["quantity"])
        new_qty = previous_qty + quantity
        previous_cost = previous_qty * float(current["average_cost"])
        new_cost = previous_cost + quantity * price + commission
        current["quantity"] = new_qty
        current["average_cost"] = new_cost / new_qty if new_qty else 0.0
        cash += float(fill.get("cash_effect", 0.0))
    else:
        sold = min(quantity, float(current["quantity"]))
        current["quantity"] = float(current["quantity"]) - sold
        if current["quantity"] <= 0:
            current["quantity"] = 0.0
            current["average_cost"] = 0.0
        cash += float(fill.get("cash_effect", 0.0))

    positions[symbol] = current
    return cash, positions

def mark_to_market(
    cash: float,
    positions: dict[str, dict[str, float]],
    prices: dict[str, float],
) -> dict[str, Any]:
    market_value = 0.0
    unrealized = 0.0
    details = {}
    for symbol, position in positions.items():
        quantity = float(position.get("quantity", 0.0))
        average_cost = float(position.get("average_cost", 0.0))
        price = float(prices.get(symbol, average_cost))
        value = quantity * price
        pnl = quantity * (price - average_cost)
        market_value += value
        unrealized += pnl
        details[symbol] = {
            "quantity": quantity,
            "average_cost": round(average_cost, 4),
            "mark_price": round(price, 4),
            "market_value": round(value, 4),
            "unrealized_pnl": round(pnl, 4),
        }
    return {
        "cash": round(cash, 4),
        "market_value": round(market_value, 4),
        "equity": round(cash + market_value, 4),
        "unrealized_pnl": round(unrealized, 4),
        "positions": details,
    }
