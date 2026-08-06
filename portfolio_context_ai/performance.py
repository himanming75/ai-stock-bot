from __future__ import annotations
from math import sqrt


def performance_metrics(returns: list[float]) -> dict:
    if not returns:
        return {
            "count": 0,
            "cumulative_return": 0.0,
            "average_return": 0.0,
            "volatility": 0.0,
            "sharpe_candidate": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
        }

    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for value in returns:
        equity *= 1.0 + value
        peak = max(peak, equity)
        drawdown = (peak - equity) / peak if peak else 0.0
        max_drawdown = max(max_drawdown, drawdown)

    average = sum(returns) / len(returns)
    variance = sum((value - average) ** 2 for value in returns) / len(returns)
    volatility = sqrt(variance)
    sharpe = average / volatility * sqrt(len(returns)) if volatility else 0.0
    win_rate = sum(1 for value in returns if value > 0) / len(returns)

    return {
        "count": len(returns),
        "cumulative_return": round(equity - 1.0, 6),
        "average_return": round(average, 6),
        "volatility": round(volatility, 6),
        "sharpe_candidate": round(sharpe, 6),
        "max_drawdown": round(max_drawdown, 6),
        "win_rate": round(win_rate, 6),
    }
