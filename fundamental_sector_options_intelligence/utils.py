from __future__ import annotations


def f(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp(value: float, low=-1.0, high=1.0) -> float:
    return max(low, min(high, value))


def signal(score: float) -> str:
    if score >= 0.20:
        return "BULLISH"
    if score <= -0.20:
        return "BEARISH"
    return "NEUTRAL"
