from __future__ import annotations
import math
import statistics
from typing import Any

def pct_returns(values: list[float]) -> list[float]:
    return [
        (current - previous) / previous
        for previous, current in zip(values, values[1:])
        if previous
    ]

def percentile(values: list[float], probability: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    probability = max(0.0, min(1.0, probability))
    index = (len(ordered) - 1) * probability
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight

def historical_var(
    returns: list[float],
    confidence: float = 0.95,
) -> float:
    if not returns:
        return 0.0
    loss_quantile = percentile(returns, 1.0 - confidence)
    return max(0.0, -loss_quantile * 100.0)

def expected_shortfall(
    returns: list[float],
    confidence: float = 0.95,
) -> float:
    if not returns:
        return 0.0
    cutoff = percentile(returns, 1.0 - confidence)
    tail = [value for value in returns if value <= cutoff]
    if not tail:
        return historical_var(returns, confidence)
    return max(0.0, -statistics.mean(tail) * 100.0)

def annualized_volatility(returns: list[float]) -> float:
    if len(returns) < 2:
        return 0.0
    return statistics.pstdev(returns) * math.sqrt(252.0) * 100.0

def max_drawdown(values: list[float]) -> float:
    if not values:
        return 0.0
    peak = values[0]
    worst = 0.0
    for value in values:
        peak = max(peak, value)
        if peak:
            worst = min(worst, (value - peak) / peak)
    return abs(worst) * 100.0

def rolling_drawdown(values: list[float]) -> list[float]:
    if not values:
        return []
    peak = values[0]
    output = []
    for value in values:
        peak = max(peak, value)
        output.append((peak - value) / peak * 100.0 if peak else 0.0)
    return output

def rolling_volatility(
    returns: list[float],
    window: int = 20,
) -> list[float]:
    output = []
    for index in range(len(returns)):
        start = max(0, index - window + 1)
        sample = returns[start:index + 1]
        output.append(
            annualized_volatility(sample) if len(sample) >= 2 else 0.0
        )
    return output

def correlation(a: list[float], b: list[float]) -> float:
    length = min(len(a), len(b))
    if length < 2:
        return 0.0
    x = a[-length:]
    y = b[-length:]
    mean_x = statistics.mean(x)
    mean_y = statistics.mean(y)
    numerator = sum(
        (left - mean_x) * (right - mean_y)
        for left, right in zip(x, y)
    )
    denominator_x = sum((value - mean_x) ** 2 for value in x)
    denominator_y = sum((value - mean_y) ** 2 for value in y)
    denominator = math.sqrt(denominator_x * denominator_y)
    return numerator / denominator if denominator else 0.0
