from __future__ import annotations
from typing import Any

def fractional_kelly(
    win_rate_pct: float,
    average_win_pct: float,
    average_loss_pct: float,
    fraction: float,
    maximum_fraction: float,
) -> dict[str, Any]:
    p=max(0.0,min(1.0,win_rate_pct/100.0))
    q=1.0-p
    loss=max(1e-9,abs(average_loss_pct))
    payoff=max(0.0,average_win_pct)/loss
    raw=(payoff*p-q)/payoff if payoff>0 else 0.0
    raw=max(0.0,raw)
    applied=min(maximum_fraction,raw*max(0.0,fraction))
    return {
        "win_rate_pct":round(win_rate_pct,6),
        "average_win_pct":round(average_win_pct,6),
        "average_loss_pct":round(average_loss_pct,6),
        "payoff_ratio":round(payoff,6),
        "raw_kelly_fraction":round(raw,6),
        "applied_kelly_fraction":round(applied,6),
    }
