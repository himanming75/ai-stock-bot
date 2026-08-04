from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class MarketInput:
    symbol: str
    close: float
    sma_fast: float
    sma_slow: float
    rsi: float
    atr_pct: float
    volume_ratio: float
    market_trend: float = 0.0
    news_score: float = 0.0

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MarketInput":
        return cls(
            symbol=str(value["symbol"]).upper().strip(),
            close=float(value["close"]),
            sma_fast=float(value["sma_fast"]),
            sma_slow=float(value["sma_slow"]),
            rsi=float(value["rsi"]),
            atr_pct=float(value["atr_pct"]),
            volume_ratio=float(value["volume_ratio"]),
            market_trend=float(value.get("market_trend", 0.0)),
            news_score=float(value.get("news_score", 0.0)),
        )


@dataclass(frozen=True)
class Decision:
    symbol: str
    action: str
    confidence: float
    regime: str
    score: float
    risk_level: str
    reasons: tuple[str, ...]
    self_review: tuple[str, ...]
    order_submission_allowed: bool = False
    actual_paper_orders_submitted: int = 0
    actual_live_orders_submitted: int = 0

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["reasons"] = list(self.reasons)
        result["self_review"] = list(self.self_review)
        return result
