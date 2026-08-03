from __future__ import annotations
import math
from typing import Any

def build_order_plan(
    allocations: list[dict[str, Any]],
    portfolio_value: float,
    position_multiplier: float,
    prices: dict[str, float],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    minimum_notional = float(policy.get("minimum_order_notional", 25.0))
    maximum_order_notional = float(policy.get("maximum_order_notional", 25000.0))
    fractional_enabled = bool(policy.get("fractional_shares_enabled", False))

    plans = []
    for row in allocations:
        strategy_id = str(row.get("strategy_id") or "")
        symbol = str(row.get("symbol") or policy.get("default_symbol", "AAPL"))
        weight = max(0.0, float(row.get("weight_pct", 0.0))) / 100.0
        price = max(0.0, float(prices.get(symbol, 0.0)))
        target_notional = portfolio_value * position_multiplier * weight
        target_notional = min(target_notional, maximum_order_notional)

        if price <= 0 or target_notional < minimum_notional:
            quantity = 0.0
            notional = 0.0
            state = "SKIPPED"
            reason = "INVALID_PRICE_OR_BELOW_MINIMUM"
        else:
            raw_quantity = target_notional / price
            quantity = round(raw_quantity, 6) if fractional_enabled else float(math.floor(raw_quantity))
            notional = round(quantity * price, 4)
            state = "PLANNED" if quantity > 0 else "SKIPPED"
            reason = "" if quantity > 0 else "ZERO_QUANTITY"

        plans.append({
            "strategy_id": strategy_id,
            "base_strategy": row.get("base_strategy"),
            "symbol": symbol,
            "side": "BUY",
            "reference_price": round(price, 4),
            "target_weight_pct": round(weight * 100.0, 4),
            "target_notional": round(target_notional, 4),
            "quantity": quantity,
            "planned_notional": notional,
            "state": state,
            "skip_reason": reason,
            "time_in_force": "DAY",
            "order_type": "MARKET_SIMULATION_ONLY",
        })
    return plans
