from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any, Mapping, Sequence


def D(value: Any, default: str = "0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


@dataclass(frozen=True)
class DataPoint:
    source: str
    value: Decimal
    confidence: Decimal = Decimal("1")
    age_seconds: int = 0

    def as_json(self) -> dict:
        return {
            "source": self.source,
            "value": str(self.value),
            "confidence": str(self.confidence),
            "age_seconds": self.age_seconds,
        }


@dataclass(frozen=True)
class FusionInput:
    symbol: str
    price_return_1d: Decimal
    price_return_5d: Decimal
    volume_ratio: Decimal
    realized_volatility: Decimal
    relative_strength: Decimal
    breadth_score: Decimal
    sector_strength: Decimal
    news_sentiment: Decimal
    news_importance: Decimal
    earnings_surprise: Decimal
    earnings_revision: Decimal
    macro_risk: Decimal
    rates_pressure: Decimal
    options_put_call: Decimal
    options_iv_rank: Decimal
    options_flow: Decimal
    liquidity_score: Decimal
    spread_bps: Decimal
    event_risk: Decimal = Decimal("0")
    source_confidence: Decimal = Decimal("1")
    source_age_seconds: int = 0

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "FusionInput":
        return cls(
            symbol=str(data["symbol"]).upper(),
            price_return_1d=D(data.get("price_return_1d")),
            price_return_5d=D(data.get("price_return_5d")),
            volume_ratio=D(data.get("volume_ratio"), "1"),
            realized_volatility=D(data.get("realized_volatility")),
            relative_strength=D(data.get("relative_strength")),
            breadth_score=D(data.get("breadth_score")),
            sector_strength=D(data.get("sector_strength")),
            news_sentiment=D(data.get("news_sentiment")),
            news_importance=D(data.get("news_importance")),
            earnings_surprise=D(data.get("earnings_surprise")),
            earnings_revision=D(data.get("earnings_revision")),
            macro_risk=D(data.get("macro_risk")),
            rates_pressure=D(data.get("rates_pressure")),
            options_put_call=D(data.get("options_put_call"), "1"),
            options_iv_rank=D(data.get("options_iv_rank")),
            options_flow=D(data.get("options_flow")),
            liquidity_score=D(data.get("liquidity_score")),
            spread_bps=D(data.get("spread_bps")),
            event_risk=D(data.get("event_risk")),
            source_confidence=D(data.get("source_confidence"), "1"),
            source_age_seconds=int(data.get("source_age_seconds", 0)),
        )


@dataclass(frozen=True)
class SymbolIntelligence:
    symbol: str
    regime: str
    composite_score: Decimal
    momentum_score: Decimal
    technical_score: Decimal
    news_score: Decimal
    earnings_score: Decimal
    macro_score: Decimal
    options_score: Decimal
    sector_score: Decimal
    liquidity_score: Decimal
    risk_penalty: Decimal
    confidence: Decimal
    trade_bias: str
    blockers: tuple[str, ...] = ()

    def as_json(self) -> dict:
        data = asdict(self)
        for key, value in list(data.items()):
            if isinstance(value, Decimal):
                data[key] = str(value)
            elif isinstance(value, tuple):
                data[key] = list(value)
        return data


@dataclass(frozen=True)
class MarketContext:
    market_regime: str
    risk_mode: str
    market_score: Decimal
    confidence: Decimal
    ranked_symbols: tuple[SymbolIntelligence, ...]
    warnings: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    source_count: int = 0

    def as_json(self) -> dict:
        return {
            "market_regime": self.market_regime,
            "risk_mode": self.risk_mode,
            "market_score": str(self.market_score),
            "confidence": str(self.confidence),
            "ranked_symbols": [item.as_json() for item in self.ranked_symbols],
            "warnings": list(self.warnings),
            "blockers": list(self.blockers),
            "source_count": self.source_count,
        }
