from __future__ import annotations
import math
from statistics import mean, pstdev


def safe_float(value, default=0.0) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def sma(values: list[float], period: int) -> float | None:
    if len(values) < period or period <= 0:
        return None
    return mean(values[-period:])


def ema_series(values: list[float], period: int) -> list[float]:
    if not values or period <= 0:
        return []
    alpha = 2.0 / (period + 1.0)
    result = [values[0]]
    for value in values[1:]:
        result.append(alpha * value + (1.0 - alpha) * result[-1])
    return result


def ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return ema_series(values, period)[-1]


def returns(values: list[float]) -> list[float]:
    result = []
    for previous, current in zip(values, values[1:]):
        if previous != 0:
            result.append(current / previous - 1.0)
    return result


def rolling_std(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return pstdev(values[-period:])


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
