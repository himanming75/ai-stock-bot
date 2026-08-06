from __future__ import annotations
import math
from .models import Bar


def sma(values: list[float], period: int) -> list[float | None]:
    result = [None] * len(values)
    if period <= 0:
        raise ValueError("INVALID_PERIOD")
    for i in range(period - 1, len(values)):
        result[i] = sum(values[i-period+1:i+1]) / period
    return result


def ema(values: list[float], period: int) -> list[float | None]:
    if period <= 0:
        raise ValueError("INVALID_PERIOD")
    result = [None] * len(values)
    if len(values) < period:
        return result
    seed = sum(values[:period]) / period
    result[period - 1] = seed
    multiplier = 2 / (period + 1)
    previous = seed
    for i in range(period, len(values)):
        previous = (values[i] - previous) * multiplier + previous
        result[i] = previous
    return result


def rsi(values: list[float], period: int = 14) -> list[float | None]:
    result = [None] * len(values)
    if len(values) <= period:
        return result
    gains = []
    losses = []
    for i in range(1, len(values)):
        change = values[i] - values[i-1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    result[period] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    for i in range(period + 1, len(values)):
        gain = gains[i-1]
        loss = losses[i-1]
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period
        result[i] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    return result


def macd(values: list[float], fast=12, slow=26, signal=9) -> dict:
    fast_values = ema(values, fast)
    slow_values = ema(values, slow)
    line = [None] * len(values)
    compact = []
    positions = []
    for i, (a, b) in enumerate(zip(fast_values, slow_values)):
        if a is not None and b is not None:
            value = a - b
            line[i] = value
            compact.append(value)
            positions.append(i)
    signal_compact = ema(compact, signal)
    signal_line = [None] * len(values)
    histogram = [None] * len(values)
    for idx, position in enumerate(positions):
        sig = signal_compact[idx]
        if sig is not None:
            signal_line[position] = sig
            histogram[position] = line[position] - sig
    return {
        "line": line,
        "signal": signal_line,
        "histogram": histogram,
    }


def true_range(bars: list[Bar]) -> list[float]:
    result = []
    for i, bar in enumerate(bars):
        if i == 0:
            result.append(bar.high - bar.low)
        else:
            previous_close = bars[i-1].close
            result.append(max(
                bar.high - bar.low,
                abs(bar.high - previous_close),
                abs(bar.low - previous_close),
            ))
    return result


def atr(bars: list[Bar], period=14) -> list[float | None]:
    return ema(true_range(bars), period)


def bollinger(values: list[float], period=20, multiplier=2.0) -> dict:
    middle = sma(values, period)
    upper = [None] * len(values)
    lower = [None] * len(values)
    width = [None] * len(values)
    for i in range(period - 1, len(values)):
        window = values[i-period+1:i+1]
        mean = middle[i]
        variance = sum((x - mean) ** 2 for x in window) / period
        std = math.sqrt(variance)
        upper[i] = mean + multiplier * std
        lower[i] = mean - multiplier * std
        width[i] = 0.0 if mean == 0 else (upper[i] - lower[i]) / mean
    return {
        "middle": middle,
        "upper": upper,
        "lower": lower,
        "width": width,
    }


def vwap(bars: list[Bar]) -> list[float]:
    cumulative_value = 0.0
    cumulative_volume = 0.0
    result = []
    for bar in bars:
        typical = (bar.high + bar.low + bar.close) / 3
        cumulative_value += typical * bar.volume
        cumulative_volume += bar.volume
        result.append(
            bar.close if cumulative_volume == 0
            else cumulative_value / cumulative_volume
        )
    return result
