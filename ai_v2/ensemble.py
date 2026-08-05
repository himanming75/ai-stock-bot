from __future__ import annotations
from decimal import Decimal
from typing import Any

from .models import StrategyScore


class StrategyEnsembleRanker:
    def score(
        self,
        *,
        strategy_id: str,
        signal_strength: Decimal,
        historical_metrics: dict[str, Any],
        regime_fit: Decimal,
        risk_penalty: Decimal,
    ) -> StrategyScore:
        win_rate = Decimal(str(historical_metrics.get("win_rate", "0.5")))
        profit_factor = Decimal(
            str(historical_metrics.get("profit_factor", "1"))
        )
        drawdown = Decimal(
            str(historical_metrics.get("maximum_drawdown", "0"))
        )

        historical_quality = (
            win_rate * Decimal("0.55")
            + min(profit_factor / Decimal("2"), Decimal("1"))
            * Decimal("0.45")
        )
        adjusted_penalty = min(
            Decimal("1"),
            max(Decimal("0"), risk_penalty + drawdown),
        )
        total = (
            signal_strength * Decimal("0.35")
            + historical_quality * Decimal("0.35")
            + regime_fit * Decimal("0.30")
            - adjusted_penalty * Decimal("0.25")
        )
        total = max(Decimal("0"), min(Decimal("1"), total))
        return StrategyScore(
            strategy_id=strategy_id,
            total_score=total.quantize(Decimal("0.0001")),
            signal_quality=signal_strength.quantize(Decimal("0.0001")),
            historical_quality=historical_quality.quantize(
                Decimal("0.0001")
            ),
            regime_fit=regime_fit.quantize(Decimal("0.0001")),
            risk_penalty=adjusted_penalty.quantize(Decimal("0.0001")),
        )

    def rank(self, scores: list[StrategyScore]) -> list[StrategyScore]:
        return sorted(
            scores,
            key=lambda item: (
                item.total_score,
                item.historical_quality,
                item.strategy_id,
            ),
            reverse=True,
        )
