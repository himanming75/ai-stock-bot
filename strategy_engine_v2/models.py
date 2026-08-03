from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class SignalInput:
    name: str
    score: float
    weight: float = 1.0
    enabled: bool = True
    reason: str = ""

    def normalized_score(self) -> float:
        return max(-100.0, min(100.0, float(self.score)))

    def normalized_weight(self) -> float:
        return max(0.0, float(self.weight))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StrategyDecision:
    symbol: str
    decision: str
    confidence: float
    composite_score: float
    bullish_count: int
    bearish_count: int
    neutral_count: int
    reasons: list[str]
    paper_only: bool = True
    broker_write_enabled: bool = False
    order_submission_enabled: bool = False
    live_trading_enabled: bool = False
    external_network_enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
