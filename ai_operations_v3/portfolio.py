from __future__ import annotations
from decimal import Decimal
from math import sqrt
from typing import Any


class PortfolioIntelligence:
    def analyze(
        self,
        *,
        positions: list[dict[str, Any]],
        correlations: dict[str, dict[str, Decimal]],
        sector_limits: dict[str, Decimal],
    ) -> dict[str, Any]:
        total_value = sum(
            Decimal(str(position["market_value"]))
            for position in positions
        )
        sector_values: dict[str, Decimal] = {}
        weights: dict[str, Decimal] = {}
        for position in positions:
            value = Decimal(str(position["market_value"]))
            symbol = position["symbol"]
            sector = position["sector"]
            weights[symbol] = (
                value / total_value if total_value > 0 else Decimal("0")
            )
            sector_values[sector] = sector_values.get(
                sector, Decimal("0")
            ) + value

        sector_rows = []
        sector_breaches = []
        for sector, value in sorted(sector_values.items()):
            weight = value / total_value if total_value > 0 else Decimal("0")
            limit = sector_limits.get(sector, Decimal("1"))
            breached = weight > limit
            if breached:
                sector_breaches.append(sector)
            sector_rows.append({
                "sector": sector,
                "market_value": str(value.quantize(Decimal("0.01"))),
                "weight": str(weight.quantize(Decimal("0.0001"))),
                "limit": str(limit),
                "breached": breached,
            })

        symbols = sorted(weights)
        matrix = []
        weighted_correlation = Decimal("0")
        pair_weight = Decimal("0")
        for left in symbols:
            row = {"symbol": left, "values": {}}
            for right in symbols:
                value = correlations.get(left, {}).get(
                    right,
                    Decimal("1") if left == right else Decimal("0"),
                )
                row["values"][right] = str(
                    value.quantize(Decimal("0.0001"))
                )
                if left < right:
                    contribution = (
                        weights[left] * weights[right] * abs(value)
                    )
                    weighted_correlation += contribution
                    pair_weight += weights[left] * weights[right]
            matrix.append(row)

        average_correlation = (
            weighted_correlation / pair_weight
            if pair_weight > 0 else Decimal("0")
        )
        concentration = sum(
            weight * weight for weight in weights.values()
        )
        diversification_score = max(
            Decimal("0"),
            min(
                Decimal("1"),
                Decimal("1")
                - concentration * Decimal("0.6")
                - average_correlation * Decimal("0.4"),
            ),
        )

        target_equal = (
            Decimal("1") / Decimal(len(symbols))
            if symbols else Decimal("0")
        )
        rebalance = []
        for symbol in symbols:
            drift = target_equal - weights[symbol]
            rebalance.append({
                "symbol": symbol,
                "current_weight": str(
                    weights[symbol].quantize(Decimal("0.0001"))
                ),
                "target_weight": str(
                    target_equal.quantize(Decimal("0.0001"))
                ),
                "weight_drift": str(
                    drift.quantize(Decimal("0.0001"))
                ),
                "suggested_direction": (
                    "BUY" if drift > Decimal("0.02")
                    else "SELL" if drift < Decimal("-0.02")
                    else "HOLD"
                ),
                "order_created": False,
            })

        return {
            "total_market_value": str(
                total_value.quantize(Decimal("0.01"))
            ),
            "position_count": len(positions),
            "sector_allocation": sector_rows,
            "sector_limit_breaches": sector_breaches,
            "correlation_matrix": matrix,
            "average_absolute_correlation": str(
                average_correlation.quantize(Decimal("0.0001"))
            ),
            "concentration_index": str(
                concentration.quantize(Decimal("0.0001"))
            ),
            "diversification_score": str(
                diversification_score.quantize(Decimal("0.0001"))
            ),
            "rebalance_preview": rebalance,
            "actual_portfolio_modified": False,
            "actual_orders_created": False,
        }
