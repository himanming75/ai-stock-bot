from __future__ import annotations
from typing import Any
from .explainability import reasons
from .models import StrategyScore, StrategySelectionResult
from .scoring import score_all
from .validation import validate


def select_strategy(payload: dict[str, Any]) -> StrategySelectionResult:
    errors = validate(payload)
    if errors:
        raise ValueError(",".join(errors))

    regime = str(payload["market_regime"]).upper()
    scored = score_all(payload)
    ranked = sorted(
        scored.items(),
        key=lambda item: (
            not item[1]["eligible"],
            -float(item[1]["score"]),
            item[0],
        ),
    )

    selected_name, selected_meta = ranked[0]
    if not selected_meta["eligible"]:
        selected_name = "CASH_DEFENSIVE"
        selected_meta = scored[selected_name]

    fallback = "CASH_DEFENSIVE"
    for name, meta in ranked:
        if name != selected_name and meta["eligible"]:
            fallback = name
            break

    strategy_scores = tuple(
        StrategyScore(
            strategy=name,
            score=float(meta["score"]),
            confidence=float(meta["confidence"]),
            eligible=bool(meta["eligible"]),
            reasons=tuple(reasons(name, payload, meta)),
        )
        for name, meta in ranked
    )

    portfolio_score = float(payload.get("portfolio_score", 0.0))
    portfolio_compatible = (
        selected_name == "CASH_DEFENSIVE"
        or portfolio_score >= float(payload.get("minimum_portfolio_score", 55.0))
    )

    return StrategySelectionResult(
        selected_strategy=selected_name,
        selected_score=float(selected_meta["score"]),
        selected_confidence=float(selected_meta["confidence"]),
        fallback_strategy=fallback,
        market_regime=regime,
        strategy_scores=strategy_scores,
        portfolio_compatible=portfolio_compatible,
    )
