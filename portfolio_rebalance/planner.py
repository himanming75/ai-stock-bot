from __future__ import annotations
from typing import Any
from portfolio_rebalance.io import digest

def build_trade_intents(
    weight_rows: list[dict[str, Any]],
    account_equity: float,
    symbol_map: dict[str, str],
    reference_prices: dict[str, Any],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    threshold = float(policy.get("minimum_rebalance_gap_pct", 2.0))
    minimum_notional = float(policy.get("minimum_trade_notional", 100.0))
    maximum_notional = float(policy.get("maximum_trade_notional", 25000.0))
    intents = []

    for row in weight_rows:
        strategy_id = row["strategy_id"]
        if strategy_id == "CASH":
            continue
        gap_pct = float(row.get("weight_gap_pct", 0.0))
        if abs(gap_pct) < threshold:
            continue

        symbol = symbol_map.get(strategy_id, "")
        price = float(reference_prices.get(symbol, 0.0))
        requested_notional = account_equity * abs(gap_pct) / 100.0
        notional = min(requested_notional, maximum_notional)
        if not symbol or price <= 0 or notional < minimum_notional:
            continue

        side = "BUY" if gap_pct > 0 else "SELL"
        quantity = notional / price
        payload = {
            "strategy_id": strategy_id,
            "symbol": symbol,
            "side": side,
            "target_weight_pct": row["target_weight_pct"],
            "current_weight_pct": row["current_weight_pct"],
            "weight_gap_pct": row["weight_gap_pct"],
            "reference_price": round(price, 6),
            "requested_notional": round(requested_notional, 6),
            "planned_notional": round(notional, 6),
            "quantity": round(quantity, 6),
        }
        payload["intent_key"] = digest(payload)
        payload["state"] = "PLANNED"
        payload["submission_allowed"] = False
        intents.append(payload)

    return intents
