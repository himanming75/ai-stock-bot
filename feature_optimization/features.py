from __future__ import annotations
from decimal import Decimal
from typing import Any


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


class TechnicalFeatureEngine:
    def build(self, bars: list[dict[str, Any]]) -> dict[str, Decimal]:
        if len(bars) < 20:
            raise ValueError("AT_LEAST_20_BARS_REQUIRED")

        closes = [_d(row["close"]) for row in bars]
        highs = [_d(row["high"]) for row in bars]
        lows = [_d(row["low"]) for row in bars]
        volumes = [_d(row["volume"]) for row in bars]

        sma_5 = sum(closes[-5:]) / Decimal("5")
        sma_10 = sum(closes[-10:]) / Decimal("10")
        sma_20 = sum(closes[-20:]) / Decimal("20")
        momentum_5 = closes[-1] / closes[-6] - Decimal("1")
        momentum_10 = closes[-1] / closes[-11] - Decimal("1")
        range_20 = max(closes[-20:]) / min(closes[-20:]) - Decimal("1")
        average_volume = sum(volumes[-20:]) / Decimal("20")
        relative_volume = (
            volumes[-1] / average_volume
            if average_volume > 0 else Decimal("0")
        )

        true_ranges = []
        for index in range(1, len(bars)):
            true_ranges.append(max(
                highs[index] - lows[index],
                abs(highs[index] - closes[index - 1]),
                abs(lows[index] - closes[index - 1]),
            ))
        atr_14 = sum(true_ranges[-14:]) / Decimal("14")

        gains = []
        losses = []
        for previous, current in zip(closes[-15:-1], closes[-14:]):
            change = current - previous
            gains.append(max(change, Decimal("0")))
            losses.append(abs(min(change, Decimal("0"))))
        avg_gain = sum(gains) / Decimal(len(gains))
        avg_loss = sum(losses) / Decimal(len(losses))
        rsi_14 = (
            Decimal("100")
            if avg_loss == 0
            else Decimal("100")
            - Decimal("100")
            / (Decimal("1") + avg_gain / avg_loss)
        )

        return {
            "last_close": closes[-1],
            "sma_5": sma_5,
            "sma_10": sma_10,
            "sma_20": sma_20,
            "trend_5_20": (sma_5 / sma_20) - Decimal("1"),
            "momentum_5": momentum_5,
            "momentum_10": momentum_10,
            "rsi_14": rsi_14,
            "atr_14": atr_14,
            "relative_volume": relative_volume,
            "range_20": range_20,
        }


class FactorEngine:
    def build(
        self,
        *,
        technical: dict[str, Decimal],
        sector_score: Decimal,
        event_score: Decimal,
        regime_score: Decimal,
    ) -> dict[str, Decimal]:
        trend = max(
            Decimal("0"),
            min(
                Decimal("1"),
                Decimal("0.5") + technical["trend_5_20"] * Decimal("5"),
            ),
        )
        momentum = max(
            Decimal("0"),
            min(
                Decimal("1"),
                Decimal("0.5") + technical["momentum_5"] * Decimal("5"),
            ),
        )
        quality = max(
            Decimal("0"),
            min(
                Decimal("1"),
                Decimal("1") - technical["range_20"],
            ),
        )
        liquidity = min(
            Decimal("1"),
            technical["relative_volume"] / Decimal("2"),
        )
        return {
            "trend_factor": trend,
            "momentum_factor": momentum,
            "quality_factor": quality,
            "liquidity_factor": liquidity,
            "sector_factor": sector_score,
            "event_factor": event_score,
            "regime_factor": regime_score,
        }
