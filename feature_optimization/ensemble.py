from __future__ import annotations
from decimal import Decimal
from typing import Any


class EnsembleScorer:
    def score(
        self,
        *,
        strategy_scores: dict[str, Decimal],
        weights: dict[str, Decimal],
    ) -> dict[str, Any]:
        total_weight = sum(weights.values(), Decimal("0"))
        if total_weight <= 0:
            raise ValueError("POSITIVE_WEIGHT_REQUIRED")

        weighted = Decimal("0")
        contributions = []
        for strategy_id in sorted(strategy_scores):
            weight = weights.get(strategy_id, Decimal("0"))
            contribution = strategy_scores[strategy_id] * weight
            weighted += contribution
            contributions.append({
                "strategy_id": strategy_id,
                "score": str(strategy_scores[strategy_id]),
                "weight": str(weight),
                "contribution": str(
                    contribution.quantize(Decimal("0.0001"))
                ),
            })

        result = weighted / total_weight
        return {
            "ensemble_score": str(
                result.quantize(Decimal("0.0001"))
            ),
            "contributions": contributions,
            "signal": (
                "BUY_PREVIEW"
                if result >= Decimal("0.70")
                else "HOLD"
            ),
            "order_created": False,
        }
