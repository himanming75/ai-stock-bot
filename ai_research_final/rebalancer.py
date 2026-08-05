from __future__ import annotations
from decimal import Decimal
from typing import Any


class PortfolioRebalancer:
    def preview(
        self,
        *,
        current_weights: dict[str, Decimal],
        target_weights: dict[str, Decimal],
        portfolio_value: Decimal,
        minimum_trade_notional: Decimal,
    ) -> dict[str, Any]:
        rows = []
        for symbol in sorted(set(current_weights) | set(target_weights)):
            current = current_weights.get(symbol, Decimal("0"))
            target = target_weights.get(symbol, Decimal("0"))
            drift = target - current
            notional = (portfolio_value * drift).quantize(Decimal("0.01"))
            action = "HOLD"
            if abs(notional) >= minimum_trade_notional:
                action = "BUY" if notional > 0 else "SELL"
            rows.append({
                "symbol": symbol,
                "current_weight": str(current),
                "target_weight": str(target),
                "weight_drift": str(drift.quantize(Decimal("0.0001"))),
                "suggested_notional": str(abs(notional)),
                "action": action,
                "order_created": False,
            })
        return {
            "rebalance_preview": rows,
            "actual_portfolio_modified": False,
            "actual_orders_created": False,
        }
