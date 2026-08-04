from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class StrategyScore:
    strategy: str
    score: float
    confidence: float
    eligible: bool
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["reasons"] = list(self.reasons)
        return value


@dataclass(frozen=True)
class StrategySelectionResult:
    selected_strategy: str
    selected_score: float
    selected_confidence: float
    fallback_strategy: str
    market_regime: str
    strategy_scores: tuple[StrategyScore, ...]
    portfolio_compatible: bool
    order_submission_allowed: bool = False
    actual_paper_orders_submitted: int = 0
    actual_live_orders_submitted: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected_strategy": self.selected_strategy,
            "selected_score": self.selected_score,
            "selected_confidence": self.selected_confidence,
            "fallback_strategy": self.fallback_strategy,
            "market_regime": self.market_regime,
            "strategy_scores": [item.to_dict() for item in self.strategy_scores],
            "portfolio_compatible": self.portfolio_compatible,
            "order_submission_allowed": self.order_submission_allowed,
            "actual_paper_orders_submitted": self.actual_paper_orders_submitted,
            "actual_live_orders_submitted": self.actual_live_orders_submitted,
        }
