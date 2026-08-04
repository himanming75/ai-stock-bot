from __future__ import annotations
import math
from typing import Any

def calculate_analytics(
    prior_daily_rows: list[dict[str, Any]],
    current_close: dict[str, Any],
    starting_equity: float,
) -> dict[str, Any]:
    rows=list(prior_daily_rows)
    current_equity=float(current_close.get("ending_equity",starting_equity))
    current_return=(
        (current_equity-starting_equity)/starting_equity
        if starting_equity else 0.0
    )
    returns=[
        float(row.get("daily_return_pct",0.0))/100.0
        for row in rows
        if isinstance(row.get("daily_return_pct"),(int,float))
    ]+[current_return]
    wins=sum(1 for value in returns if value>0)
    losses=sum(1 for value in returns if value<0)
    mean=sum(returns)/len(returns) if returns else 0.0
    variance=(
        sum((x-mean)**2 for x in returns)/(len(returns)-1)
        if len(returns)>1 else 0.0
    )
    volatility=math.sqrt(variance)
    sharpe=(mean/volatility*math.sqrt(252)) if volatility>0 else 0.0
    peak=starting_equity
    max_dd=0.0
    equity=starting_equity
    for value in returns:
        equity*=1+value
        peak=max(peak,equity)
        drawdown=(peak-equity)/peak if peak else 0.0
        max_dd=max(max_dd,drawdown)
    return {
        "observation_count":len(returns),
        "daily_return_pct":round(current_return*100,6),
        "cumulative_return_pct":round(
            (
                (current_equity/starting_equity-1)*100
                if starting_equity else 0.0
            ),
            6,
        ),
        "win_count":wins,
        "loss_count":losses,
        "win_rate_pct":round(
            wins/max(1,wins+losses)*100,6
        ),
        "annualized_sharpe":round(sharpe,6),
        "maximum_drawdown_pct":round(max_dd*100,6),
        "ending_equity":round(current_equity,2),
    }
