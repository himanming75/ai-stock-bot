from __future__ import annotations
from decimal import Decimal
from typing import Any

from .indicators import TechnicalIndicatorEngine


class StockScanner:
    def __init__(self) -> None:
        self.indicators = TechnicalIndicatorEngine()

    def score_symbol(
        self,
        *,
        symbol: str,
        bars: list[dict[str, Any]],
        sector_score: Decimal,
        event_score: Decimal,
        regime_multiplier: Decimal,
    ) -> dict[str, Any]:
        indicators = self.indicators.calculate(bars)
        close = Decimal(indicators["last_close"])
        sma_5 = Decimal(indicators["sma_5"])
        sma_20 = Decimal(indicators["sma_20"])
        momentum = Decimal(indicators["momentum_5"])
        rsi = Decimal(indicators["rsi_14"])
        relative_volume = Decimal(indicators["relative_volume"])
        volatility = Decimal(indicators["volatility_20"])

        trend = Decimal("1") if close > sma_5 > sma_20 else Decimal("0.35")
        momentum_component = max(
            Decimal("0"),
            min(Decimal("1"), Decimal("0.5") + momentum * Decimal("5")),
        )
        rsi_component = max(
            Decimal("0"),
            Decimal("1") - abs(rsi - Decimal("55")) / Decimal("55"),
        )
        volume_component = min(Decimal("1"), relative_volume / Decimal("2"))
        volatility_penalty = min(Decimal("0.35"), volatility)

        technical = (
            trend * Decimal("0.35")
            + momentum_component * Decimal("0.25")
            + rsi_component * Decimal("0.20")
            + volume_component * Decimal("0.20")
            - volatility_penalty
        )
        total = (
            technical * Decimal("0.55")
            + sector_score * Decimal("0.20")
            + event_score * Decimal("0.15")
        ) * regime_multiplier
        total = max(Decimal("0"), min(Decimal("1"), total))

        return {
            "symbol": symbol,
            "technical_score": str(technical.quantize(Decimal("0.0001"))),
            "sector_score": str(sector_score.quantize(Decimal("0.0001"))),
            "event_score": str(event_score.quantize(Decimal("0.0001"))),
            "regime_multiplier": str(regime_multiplier.quantize(Decimal("0.0001"))),
            "total_score": str(total.quantize(Decimal("0.0001"))),
            "indicators": indicators,
        }

    def rank(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return sorted(
            rows,
            key=lambda item: (Decimal(item["total_score"]), item["symbol"]),
            reverse=True,
        )
