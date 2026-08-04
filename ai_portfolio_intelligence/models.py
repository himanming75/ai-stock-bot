from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class PortfolioCandidate:
    symbol: str
    sector: str
    action: str
    confidence: float
    signal_rank: str
    signal_score: float
    risk_score: int
    risk_level: str
    expected_holding_days: str
    liquidity_score: float
    selected: bool
    weight: float
    selection_score: float
    reasons: tuple[str, ...]
    exclusion_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["reasons"] = list(self.reasons)
        value["exclusion_reasons"] = list(self.exclusion_reasons)
        return value


@dataclass(frozen=True)
class PortfolioResult:
    selected: tuple[PortfolioCandidate, ...]
    excluded: tuple[PortfolioCandidate, ...]
    cash_weight: float
    portfolio_score: float
    diversification_score: float
    total_selected_weight: float
    order_submission_allowed: bool = False
    actual_paper_orders_submitted: int = 0
    actual_live_orders_submitted: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected": [item.to_dict() for item in self.selected],
            "excluded": [item.to_dict() for item in self.excluded],
            "cash_weight": self.cash_weight,
            "portfolio_score": self.portfolio_score,
            "diversification_score": self.diversification_score,
            "total_selected_weight": self.total_selected_weight,
            "order_submission_allowed": self.order_submission_allowed,
            "actual_paper_orders_submitted": self.actual_paper_orders_submitted,
            "actual_live_orders_submitted": self.actual_live_orders_submitted,
        }
