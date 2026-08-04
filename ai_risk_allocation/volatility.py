from __future__ import annotations


def volatility_multiplier(
    target_volatility: float,
    observed_volatility: float,
    minimum_multiplier: float,
    maximum_multiplier: float,
) -> float:
    if target_volatility <= 0:
        raise ValueError("TARGET_VOLATILITY_MUST_BE_POSITIVE")
    if observed_volatility <= 0:
        raise ValueError("OBSERVED_VOLATILITY_MUST_BE_POSITIVE")
    if not 0 < minimum_multiplier <= maximum_multiplier:
        raise ValueError("VOLATILITY_MULTIPLIER_BOUNDS_INVALID")

    raw = target_volatility / observed_volatility
    return max(minimum_multiplier, min(maximum_multiplier, raw))
