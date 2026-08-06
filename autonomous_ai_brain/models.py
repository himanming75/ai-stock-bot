from __future__ import annotations
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class StrategyCandidate:
    strategy_id: str
    signal: str
    confidence: Decimal
    expected_return: Decimal
    drawdown_risk: Decimal
    regime_fit: Decimal
    stability: Decimal
    evidence_count: int
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for key in (
            "confidence",
            "expected_return",
            "drawdown_risk",
            "regime_fit",
            "stability",
        ):
            value[key] = str(value[key])
        return value


@dataclass(frozen=True)
class StrategyScore:
    strategy_id: str
    total_score: Decimal
    rank: int
    eligible: bool
    rejection_reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["total_score"] = str(value["total_score"])
        value["rejection_reasons"] = list(
            self.rejection_reasons
        )
        return value


@dataclass(frozen=True)
class BrainDecision:
    action: str
    selected_strategy_id: str | None
    confidence: Decimal
    autonomous_state: str
    reason: str
    promotion_recommended: bool
    automatic_promotion_performed: bool
    order_submission_allowed: bool

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["confidence"] = str(value["confidence"])
        return value
