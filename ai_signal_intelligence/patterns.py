from __future__ import annotations
from collections.abc import Sequence
from .models import Bar


def detect(bars: Sequence[Bar]) -> list[str]:
    if not bars:
        return []
    current = bars[-1]
    body = abs(current.close - current.open)
    candle_range = max(current.high - current.low, 1e-12)
    upper = current.high - max(current.open, current.close)
    lower = min(current.open, current.close) - current.low
    patterns: list[str] = []

    if body / candle_range <= 0.1:
        patterns.append("DOJI")
    if lower >= body * 2 and upper <= max(body, candle_range * 0.1):
        patterns.append("HAMMER")
    if upper >= body * 2 and lower <= max(body, candle_range * 0.1):
        patterns.append("SHOOTING_STAR")

    if len(bars) >= 2:
        previous = bars[-2]
        if (
            current.close > current.open
            and previous.close < previous.open
            and current.open <= previous.close
            and current.close >= previous.open
        ):
            patterns.append("BULLISH_ENGULFING")
        if (
            current.close < current.open
            and previous.close > previous.open
            and current.open >= previous.close
            and current.close <= previous.open
        ):
            patterns.append("BEARISH_ENGULFING")
    return patterns
