from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class PositionSize:
    symbol: str
    sector: str
    reference_price: float
    stop_loss_pct: float
    proposed_weight: float
    risk_budget: float
    maximum_notional_by_risk: float
    maximum_notional_by_weight: float
    recommended_notional: float
    recommended_quantity: float
    effective_weight: float
    risk_at_stop: float
    binding_constraint: str
    status: str
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["reasons"] = list(self.reasons)
        return value


@dataclass(frozen=True)
class PositionSizingResult:
    account_equity: float
    risk_per_trade_pct: float
    maximum_position_pct: float
    positions: tuple[PositionSize, ...]
    total_recommended_notional: float
    total_effective_weight: float
    total_risk_at_stop: float
    remaining_cash: float
    order_submission_allowed: bool = False
    actual_paper_orders_submitted: int = 0
    actual_live_orders_submitted: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "account_equity": self.account_equity,
            "risk_per_trade_pct": self.risk_per_trade_pct,
            "maximum_position_pct": self.maximum_position_pct,
            "positions": [item.to_dict() for item in self.positions],
            "total_recommended_notional": self.total_recommended_notional,
            "total_effective_weight": self.total_effective_weight,
            "total_risk_at_stop": self.total_risk_at_stop,
            "remaining_cash": self.remaining_cash,
            "order_submission_allowed": self.order_submission_allowed,
            "actual_paper_orders_submitted": self.actual_paper_orders_submitted,
            "actual_live_orders_submitted": self.actual_live_orders_submitted,
        }
