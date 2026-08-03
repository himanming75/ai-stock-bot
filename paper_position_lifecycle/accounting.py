from __future__ import annotations
from typing import Any

def close_position(
    symbol: str,
    position: dict[str, Any],
    exit_price: float,
    commission_per_share: float = 0.0,
) -> dict[str, Any]:
    quantity = float(position.get("quantity", 0.0))
    average_cost = float(position.get("average_cost", 0.0))
    commission = max(0.0, quantity * commission_per_share)
    gross_proceeds = quantity * exit_price
    cost_basis = quantity * average_cost
    realized_pnl = gross_proceeds - cost_basis - commission
    return {
        "symbol": symbol,
        "closed_quantity": quantity,
        "average_cost": round(average_cost, 4),
        "exit_price": round(exit_price, 4),
        "gross_proceeds": round(gross_proceeds, 4),
        "cost_basis": round(cost_basis, 4),
        "commission": round(commission, 4),
        "realized_pnl": round(realized_pnl, 4),
        "realized_return_pct": round(
            realized_pnl / cost_basis * 100.0 if cost_basis else 0.0,
            4,
        ),
    }
