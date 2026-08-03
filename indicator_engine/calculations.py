from __future__ import annotations

from typing import Iterable

from indicator_engine.models import Bar


def sma(values: list[float], period: int) -> float | None:
    if period <= 0:
        raise ValueError("period must be positive")
    if len(values) < period:
        return None
    window = values[-period:]
    return sum(window) / period


def ema_series(values: list[float], period: int) -> list[float]:
    if period <= 0:
        raise ValueError("period must be positive")
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    output = [float(values[0])]
    for value in values[1:]:
        output.append((float(value) * alpha) + (output[-1] * (1.0 - alpha)))
    return output


def ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return ema_series(values, period)[-1]


def rsi(values: list[float], period: int = 14) -> float | None:
    if period <= 0:
        raise ValueError("period must be positive")
    if len(values) <= period:
        return None

    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    recent = changes[-period:]
    gains = [max(change, 0.0) for change in recent]
    losses = [abs(min(change, 0.0)) for change in recent]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    relative_strength = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))


def macd(
    values: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, float | None]:
    if fast <= 0 or slow <= 0 or signal <= 0:
        raise ValueError("periods must be positive")
    if fast >= slow:
        raise ValueError("fast period must be less than slow period")
    if len(values) < slow:
        return {"macd": None, "signal": None, "histogram": None}

    fast_series = ema_series(values, fast)
    slow_series = ema_series(values, slow)
    line = [a - b for a, b in zip(fast_series, slow_series)]
    signal_series = ema_series(line, signal)
    macd_value = line[-1]
    signal_value = signal_series[-1]
    return {
        "macd": macd_value,
        "signal": signal_value,
        "histogram": macd_value - signal_value,
    }


def true_ranges(bars: list[Bar]) -> list[float]:
    if not bars:
        return []
    output = [bars[0].high - bars[0].low]
    for previous, current in zip(bars, bars[1:]):
        output.append(max(
            current.high - current.low,
            abs(current.high - previous.close),
            abs(current.low - previous.close),
        ))
    return output


def atr(bars: list[Bar], period: int = 14) -> float | None:
    ranges = true_ranges(bars)
    return sma(ranges, period)


def bollinger_bands(
    values: list[float],
    period: int = 20,
    deviations: float = 2.0,
) -> dict[str, float | None]:
    middle = sma(values, period)
    if middle is None:
        return {"upper": None, "middle": None, "lower": None, "width_pct": None}

    window = values[-period:]
    variance = sum((value - middle) ** 2 for value in window) / period
    std = variance ** 0.5
    upper = middle + (deviations * std)
    lower = middle - (deviations * std)
    width_pct = ((upper - lower) / middle * 100.0) if middle else 0.0
    return {
        "upper": upper,
        "middle": middle,
        "lower": lower,
        "width_pct": width_pct,
    }


def vwap(bars: list[Bar]) -> float | None:
    total_volume = sum(bar.volume for bar in bars)
    if not bars or total_volume <= 0:
        return None
    weighted = sum(
        ((bar.high + bar.low + bar.close) / 3.0) * bar.volume
        for bar in bars
    )
    return weighted / total_volume
