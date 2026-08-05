from __future__ import annotations
from decimal import Decimal
from .models import StrategyCandidate, EnsembleDecision

class StrategyEnsembleV4:
    def decide(
        self,
        *,
        candidates: list[StrategyCandidate],
        market_regime: str,
        minimum_confidence: Decimal = Decimal("0.55"),
        maximum_single_weight: Decimal = Decimal("0.45"),
    ) -> EnsembleDecision:
        if not candidates:
            return EnsembleDecision(
                action="HOLD",
                confidence=Decimal("0"),
                selected_strategy_ids=(),
                normalized_weights={},
                explanation=("NO_STRATEGY_CANDIDATES",),
                blocked=True,
                blockers=("NO_STRATEGY_CANDIDATES",),
            )

        regime_boosts = {
            "TRENDING": {"momentum": Decimal("0.12"), "breakout": Decimal("0.10")},
            "RANGING": {"mean_reversion": Decimal("0.12")},
            "HIGH_VOLATILITY": {"volatility": Decimal("0.08")},
            "LOW_VOLATILITY": {"swing": Decimal("0.06")},
        }
        raw: dict[str, Decimal] = {}
        explanations: list[str] = []
        for item in candidates:
            score = (
                item.signal_strength * Decimal("0.25")
                + item.historical_quality * Decimal("0.20")
                + item.regime_fit * Decimal("0.20")
                + item.recent_performance * Decimal("0.20")
                - item.correlation_penalty * Decimal("0.075")
                - item.risk_penalty * Decimal("0.075")
            )
            for key, boost in regime_boosts.get(market_regime, {}).items():
                if key in item.strategy_id.lower():
                    score += boost
                    explanations.append(f"REGIME_BOOST:{item.strategy_id}")
            raw[item.strategy_id] = max(Decimal("0"), score)

        total = sum(raw.values(), Decimal("0"))
        if total <= 0:
            return EnsembleDecision(
                action="HOLD",
                confidence=Decimal("0"),
                selected_strategy_ids=(),
                normalized_weights={},
                explanation=tuple(explanations + ["NON_POSITIVE_ENSEMBLE_SCORE"]),
                blocked=True,
                blockers=("NON_POSITIVE_ENSEMBLE_SCORE",),
            )

        weights = {k: v / total for k, v in raw.items()}
        capped = {k: min(v, maximum_single_weight) for k, v in weights.items()}
        cap_total = sum(capped.values(), Decimal("0"))
        normalized = {k: (v / cap_total).quantize(Decimal("0.0001")) for k, v in capped.items()}
        average_quality = sum(raw.values(), Decimal("0")) / Decimal(str(len(raw)))
        diversity_quality = Decimal("1") - max(normalized.values())
        confidence = min(
            Decimal("1"),
            average_quality * Decimal("0.80")
            + diversity_quality * Decimal("0.20"),
        ).quantize(Decimal("0.0001"))
        blocked = confidence < minimum_confidence
        selected = tuple(k for k, v in sorted(normalized.items(), key=lambda x: x[1], reverse=True) if v >= Decimal("0.10"))
        return EnsembleDecision(
            action="HOLD" if blocked else "TRADE",
            confidence=confidence,
            selected_strategy_ids=selected,
            normalized_weights=normalized,
            explanation=tuple(explanations + [
                f"MARKET_REGIME:{market_regime}",
                f"MAX_SINGLE_WEIGHT:{maximum_single_weight}",
                f"CONFIDENCE:{confidence}",
            ]),
            blocked=blocked,
            blockers=("LOW_ENSEMBLE_CONFIDENCE",) if blocked else (),
        )
