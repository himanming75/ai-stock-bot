from __future__ import annotations
from typing import Any


def full_kelly(win_rate: float, average_win: float, average_loss: float) -> float:
    if not 0.0 <= win_rate <= 1.0:
        raise ValueError("WIN_RATE_OUT_OF_RANGE")
    if average_win <= 0:
        raise ValueError("AVERAGE_WIN_MUST_BE_POSITIVE")
    if average_loss <= 0:
        raise ValueError("AVERAGE_LOSS_MUST_BE_POSITIVE")

    reward_risk = average_win / average_loss
    loss_rate = 1.0 - win_rate
    value = win_rate - (loss_rate / reward_risk)
    return max(0.0, value)


def adjusted_kelly(
    win_rate: float,
    average_win: float,
    average_loss: float,
    fraction: float,
    maximum_kelly_pct: float,
) -> dict[str, float]:
    if not 0.0 < fraction <= 1.0:
        raise ValueError("KELLY_FRACTION_OUT_OF_RANGE")
    if not 0.0 < maximum_kelly_pct <= 1.0:
        raise ValueError("MAXIMUM_KELLY_PCT_OUT_OF_RANGE")

    full = full_kelly(win_rate, average_win, average_loss)
    fractional = full * fraction
    capped = min(fractional, maximum_kelly_pct)

    return {
        "reward_risk_ratio": round(average_win / average_loss, 6),
        "full_kelly_pct": round(full, 6),
        "fractional_kelly_pct": round(fractional, 6),
        "capped_kelly_pct": round(capped, 6),
    }
