from __future__ import annotations


def clamp(value: float, low=-1.0, high=1.0) -> float:
    return max(low, min(high, value))


def f(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_100(value) -> float:
    return clamp(f(value) / 100.0)


def signal(score: float) -> str:
    if score >= 0.22:
        return "BUY_CANDIDATE"
    if score <= -0.22:
        return "SELL_OR_AVOID"
    return "HOLD_OR_NEUTRAL"
