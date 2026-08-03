from __future__ import annotations
from typing import Any

def strategy_symbol_map(policy: dict[str, Any]) -> dict[str, str]:
    output = {}
    for row in policy.get("strategy_symbol_map", []):
        strategy_id = str(row.get("strategy_id", ""))
        symbol = str(row.get("symbol", "")).upper()
        if strategy_id and symbol:
            output[strategy_id] = symbol
    return output

def build_strategy_positions(
    account_result: dict[str, Any],
    portfolio_result: dict[str, Any],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    positions = account_result.get("reported_positions", {})
    symbol_map = strategy_symbol_map(policy)
    allocations = portfolio_result.get("allocation", {}).get("allocations", [])
    rows = []

    for allocation in allocations:
        strategy_id = str(allocation.get("strategy_id", ""))
        symbol = symbol_map.get(strategy_id, "")
        source = positions.get(symbol, {}) if symbol else {}
        market_value = float(source.get("market_value", 0.0))
        if abs(market_value) <= 1e-12:
            quantity = float(source.get("quantity", 0.0))
            mark_price = float(
                source.get("mark_price", source.get("average_cost", 0.0))
            )
            market_value = quantity * mark_price
        rows.append({
            "strategy_id": strategy_id,
            "symbol": symbol,
            "quantity": float(source.get("quantity", 0.0)),
            "average_cost": float(source.get("average_cost", 0.0)),
            "mark_price": float(
                source.get("mark_price", source.get("average_cost", 0.0))
            ),
            "market_value": round(market_value, 6),
        })
    return rows
