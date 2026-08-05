from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

@dataclass(frozen=True)
class StrategyCandidate:
    strategy_id: str
    signal_strength: Decimal
    historical_quality: Decimal
    regime_fit: Decimal
    recent_performance: Decimal
    correlation_penalty: Decimal
    risk_penalty: Decimal

@dataclass(frozen=True)
class EnsembleDecision:
    action: str
    confidence: Decimal
    selected_strategy_ids: tuple[str, ...]
    normalized_weights: dict[str, Decimal]
    explanation: tuple[str, ...]
    blocked: bool
    blockers: tuple[str, ...]

    def as_json(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "confidence": str(self.confidence),
            "selected_strategy_ids": list(self.selected_strategy_ids),
            "normalized_weights": {
                k: str(v) for k, v in self.normalized_weights.items()
            },
            "explanation": list(self.explanation),
            "blocked": self.blocked,
            "blockers": list(self.blockers),
        }

@dataclass(frozen=True)
class RiskBudgetDecision:
    symbol: str
    approved_notional: Decimal
    risk_multiplier: Decimal
    blocked: bool
    blockers: tuple[str, ...]

@dataclass(frozen=True)
class PortfolioAllocation:
    symbol: str
    target_weight: Decimal
    target_notional: Decimal
    rebalance_required: bool
    blockers: tuple[str, ...]

@dataclass(frozen=True)
class ExecutionPlan:
    symbol: str
    side: str
    order_type: str
    total_quantity: Decimal
    slice_count: int
    limit_price: Decimal | None
    expected_slippage_bps: Decimal
    time_limit_seconds: int
    blocked: bool
    blockers: tuple[str, ...]
