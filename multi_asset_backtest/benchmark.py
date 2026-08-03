from __future__ import annotations

from backtest_v2.models import Bar


def buy_and_hold(
    bars: list[Bar],
    initial_cash: float,
) -> dict:
    if not bars:
        return {
            "initial_cash": initial_cash,
            "ending_equity": initial_cash,
            "total_return_pct": 0.0,
        }

    quantity = initial_cash / bars[0].close if bars[0].close > 0 else 0.0
    ending_equity = quantity * bars[-1].close
    total_return_pct = (
        (ending_equity - initial_cash) / initial_cash * 100.0
        if initial_cash
        else 0.0
    )
    return {
        "initial_cash": round(initial_cash, 4),
        "ending_equity": round(ending_equity, 4),
        "total_return_pct": round(total_return_pct, 4),
    }
