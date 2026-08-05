from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class StrategyScore:
    strategy_id: str
    total_score: Decimal
    signal_quality: Decimal
    historical_quality: Decimal
    regime_fit: Decimal
    risk_penalty: Decimal

    def as_json(self) -> dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "total_score": str(self.total_score),
            "signal_quality": str(self.signal_quality),
            "historical_quality": str(self.historical_quality),
            "regime_fit": str(self.regime_fit),
            "risk_penalty": str(self.risk_penalty),
        }


@dataclass(frozen=True)
class PortfolioTarget:
    symbol: str
    target_weight: Decimal
    target_notional: Decimal
    confidence: Decimal

    def as_json(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "target_weight": str(self.target_weight),
            "target_notional": str(self.target_notional),
            "confidence": str(self.confidence),
        }


@dataclass(frozen=True)
class DynamicRiskDecision:
    symbol: str
    base_notional: Decimal
    adjusted_notional: Decimal
    volatility_multiplier: Decimal
    drawdown_multiplier: Decimal
    correlation_multiplier: Decimal
    blocked: bool
    blockers: tuple[str, ...]

    def as_json(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "base_notional": str(self.base_notional),
            "adjusted_notional": str(self.adjusted_notional),
            "volatility_multiplier": str(self.volatility_multiplier),
            "drawdown_multiplier": str(self.drawdown_multiplier),
            "correlation_multiplier": str(self.correlation_multiplier),
            "blocked": self.blocked,
            "blockers": list(self.blockers),
        }
