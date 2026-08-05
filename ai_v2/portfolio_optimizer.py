from __future__ import annotations
from decimal import Decimal
from typing import Any

from .models import PortfolioTarget


class PortfolioOptimizer:
    def optimize(
        self,
        *,
        symbol_scores: dict[str, Decimal],
        total_capital: Decimal,
        maximum_symbol_weight: Decimal,
        cash_reserve_weight: Decimal,
    ) -> dict[str, Any]:
        if total_capital <= 0:
            raise ValueError("TOTAL_CAPITAL_MUST_BE_POSITIVE")
        if not symbol_scores:
            return {
                "targets": [],
                "cash_weight": "1",
                "invested_weight": "0",
                "actual_portfolio_modified": False,
            }

        usable_weight = max(
            Decimal("0"),
            Decimal("1") - cash_reserve_weight,
        )
        positive = {
            symbol: max(Decimal("0"), score)
            for symbol, score in symbol_scores.items()
        }
        total_score = sum(positive.values(), Decimal("0"))
        if total_score <= 0:
            return {
                "targets": [],
                "cash_weight": "1",
                "invested_weight": "0",
                "actual_portfolio_modified": False,
            }

        raw = {
            symbol: min(
                maximum_symbol_weight,
                usable_weight * score / total_score,
            )
            for symbol, score in positive.items()
            if score > 0
        }
        assigned = sum(raw.values(), Decimal("0"))

        # Unused weight remains cash rather than being forced into positions.
        targets = [
            PortfolioTarget(
                symbol=symbol,
                target_weight=weight.quantize(Decimal("0.0001")),
                target_notional=(
                    total_capital * weight
                ).quantize(Decimal("0.01")),
                confidence=positive[symbol].quantize(
                    Decimal("0.0001")
                ),
            )
            for symbol, weight in sorted(raw.items())
        ]
        return {
            "targets": [target.as_json() for target in targets],
            "cash_weight": str(
                (Decimal("1") - assigned).quantize(Decimal("0.0001"))
            ),
            "invested_weight": str(
                assigned.quantize(Decimal("0.0001"))
            ),
            "actual_portfolio_modified": False,
        }
