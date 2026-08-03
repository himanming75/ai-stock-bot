from __future__ import annotations
import statistics
from typing import Any

def sma(values: list[float], period: int) -> float | None:
    if period <= 0 or len(values) < period:
        return None
    return sum(values[-period:]) / period

def pct_returns(values: list[float]) -> list[float]:
    return [
        (b-a)/a for a,b in zip(values, values[1:]) if a
    ]

def annualized_volatility(values: list[float]) -> float:
    returns = pct_returns(values)
    if len(returns) < 2:
        return 0.0
    return statistics.pstdev(returns) * (252 ** 0.5) * 100.0

def momentum(values: list[float], period: int) -> float:
    if len(values) <= period:
        return 0.0
    return (values[-1] / values[-period-1] - 1.0) * 100.0

def average_true_range_pct(bars: list[dict[str, Any]], period: int = 14) -> float:
    if len(bars) < 2:
        return 0.0
    trs = []
    for prev, cur in zip(bars, bars[1:]):
        high = float(cur["high"])
        low = float(cur["low"])
        prev_close = float(prev["close"])
        trs.append(max(high-low, abs(high-prev_close), abs(low-prev_close)))
    sample = trs[-period:] if len(trs) >= period else trs
    close = float(bars[-1]["close"])
    return (sum(sample)/len(sample))/close*100.0 if sample and close else 0.0

def trend_slope_pct(values: list[float], period: int = 20) -> float:
    if len(values) < period:
        return 0.0
    sample = values[-period:]
    if sample[0] == 0:
        return 0.0
    return (sample[-1]/sample[0]-1.0)*100.0
