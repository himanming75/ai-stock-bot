from __future__ import annotations
from collections.abc import Sequence
from .models import Bar


def ema(values: Sequence[float], period: int) -> float:
    if not values or period <= 0:
        raise ValueError("EMA_INPUT_INVALID")
    alpha = 2.0 / (period + 1.0)
    result = float(values[0])
    for value in values[1:]:
        result = alpha * float(value) + (1.0 - alpha) * result
    return result


def rsi(values: Sequence[float], period: int = 14) -> float:
    if len(values) < 2:
        return 50.0
    changes = [float(values[i]) - float(values[i - 1]) for i in range(1, len(values))]
    window = changes[-period:]
    gains = sum(max(change, 0.0) for change in window) / len(window)
    losses = sum(max(-change, 0.0) for change in window) / len(window)
    if losses == 0:
        return 100.0 if gains else 50.0
    rs = gains / losses
    return 100.0 - (100.0 / (1.0 + rs))


def atr_pct(bars: Sequence[Bar], period: int = 14) -> float:
    if not bars:
        raise ValueError("BARS_REQUIRED")
    ranges: list[float] = []
    previous_close = bars[0].close
    for bar in bars:
        ranges.append(max(
            bar.high - bar.low,
            abs(bar.high - previous_close),
            abs(bar.low - previous_close),
        ))
        previous_close = bar.close
    atr = sum(ranges[-period:]) / len(ranges[-period:])
    return atr / bars[-1].close if bars[-1].close else 0.0


def volume_ratio(bars: Sequence[Bar], period: int = 20) -> float:
    if not bars:
        raise ValueError("BARS_REQUIRED")
    previous = [bar.volume for bar in bars[:-1][-period:]]
    if not previous:
        return 1.0
    average = sum(previous) / len(previous)
    return bars[-1].volume / average if average else 1.0


def macd_histogram(values: Sequence[float]) -> float:
    fast = ema(values, 12)
    slow = ema(values, 26)
    macd = fast - slow
    # A compact deterministic approximation suitable for the offline foundation.
    signal = macd * 0.8
    scale = values[-1] if values and values[-1] else 1.0
    return (macd - signal) / scale
