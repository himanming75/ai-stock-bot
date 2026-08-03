from __future__ import annotations


def moving_average(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def crossover_signal(
    closes: list[float],
    fast_period: int,
    slow_period: int,
) -> str:
    if len(closes) < slow_period + 1:
        return "HOLD"

    prev_fast = moving_average(closes[:-1], fast_period)
    prev_slow = moving_average(closes[:-1], slow_period)
    curr_fast = moving_average(closes, fast_period)
    curr_slow = moving_average(closes, slow_period)

    if None in {prev_fast, prev_slow, curr_fast, curr_slow}:
        return "HOLD"

    if prev_fast <= prev_slow and curr_fast > curr_slow:
        return "BUY"
    if prev_fast >= prev_slow and curr_fast < curr_slow:
        return "SELL"
    return "HOLD"
