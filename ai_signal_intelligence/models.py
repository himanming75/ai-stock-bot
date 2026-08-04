from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class Bar:
    open: float
    high: float
    low: float
    close: float
    volume: float

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Bar":
        return cls(*(float(value[k]) for k in ("open", "high", "low", "close", "volume")))


@dataclass(frozen=True)
class SignalResult:
    symbol: str
    action: str
    confidence: float
    signal_rank: str
    signal_score: float
    risk_score: int
    risk_level: str
    regime: str
    patterns: tuple[str, ...]
    components: dict[str, float]
    reasons: tuple[str, ...]
    self_review: tuple[str, ...]
    expected_holding_days: str
    order_submission_allowed: bool = False
    actual_paper_orders_submitted: int = 0
    actual_live_orders_submitted: int = 0

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["patterns"] = list(self.patterns)
        value["reasons"] = list(self.reasons)
        value["self_review"] = list(self.self_review)
        return value
