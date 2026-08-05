from __future__ import annotations
from decimal import Decimal
from typing import Any


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


class TechnicalIndicatorEngine:
    def calculate(self, bars: list[dict[str, Any]]) -> dict[str, Any]:
        if len(bars) < 20:
            raise ValueError("AT_LEAST_20_BARS_REQUIRED")

        closes = [_d(bar["close"]) for bar in bars]
        highs = [_d(bar["high"]) for bar in bars]
        lows = [_d(bar["low"]) for bar in bars]
        volumes = [_d(bar["volume"]) for bar in bars]

        sma_5 = sum(closes[-5:]) / Decimal("5")
        sma_20 = sum(closes[-20:]) / Decimal("20")
        momentum_5 = closes[-1] / closes[-6] - Decimal("1")

        gains = []
        losses = []
        for previous, current in zip(closes[-15:-1], closes[-14:]):
            change = current - previous
            gains.append(max(change, Decimal("0")))
            losses.append(abs(min(change, Decimal("0"))))
        average_gain = sum(gains) / Decimal(len(gains))
        average_loss = sum(losses) / Decimal(len(losses))
        if average_loss == 0:
            rsi_14 = Decimal("100")
        else:
            rs = average_gain / average_loss
            rsi_14 = Decimal("100") - Decimal("100") / (Decimal("1") + rs)

        true_ranges = []
        for index in range(1, len(bars)):
            high = highs[index]
            low = lows[index]
            previous_close = closes[index - 1]
            true_ranges.append(max(
                high - low,
                abs(high - previous_close),
                abs(low - previous_close),
            ))
        atr_14 = sum(true_ranges[-14:]) / Decimal("14")
        average_volume_20 = sum(volumes[-20:]) / Decimal("20")
        relative_volume = (
            volumes[-1] / average_volume_20
            if average_volume_20 > 0 else Decimal("0")
        )
        volatility_20 = max(closes[-20:]) / min(closes[-20:]) - Decimal("1")

        return {
            "last_close": str(closes[-1].quantize(Decimal("0.0001"))),
            "sma_5": str(sma_5.quantize(Decimal("0.0001"))),
            "sma_20": str(sma_20.quantize(Decimal("0.0001"))),
            "momentum_5": str(momentum_5.quantize(Decimal("0.0001"))),
            "rsi_14": str(rsi_14.quantize(Decimal("0.0001"))),
            "atr_14": str(atr_14.quantize(Decimal("0.0001"))),
            "relative_volume": str(relative_volume.quantize(Decimal("0.0001"))),
            "volatility_20": str(volatility_20.quantize(Decimal("0.0001"))),
        }
