from __future__ import annotations

import math
import statistics
from typing import Any


def max_drawdown(equity_curve: list[float]) -> tuple[float, list[float]]:
    if not equity_curve:
        return 0.0, []
    peak = equity_curve[0]
    maximum = 0.0
    curve = []
    for equity in equity_curve:
        peak = max(peak, equity)
        drawdown = ((equity - peak) / peak * 100.0) if peak else 0.0
        curve.append(drawdown)
        maximum = min(maximum, drawdown)
    return abs(maximum), curve


def periodic_returns(equity_curve: list[float]) -> list[float]:
    output = []
    for previous, current in zip(equity_curve, equity_curve[1:]):
        if previous:
            output.append((current - previous) / previous)
    return output


def annualized_sharpe(returns: list[float], periods: int = 252) -> float:
    if len(returns) < 2:
        return 0.0
    std = statistics.pstdev(returns)
    if std == 0:
        return 0.0
    return statistics.mean(returns) / std * math.sqrt(periods)


def annualized_sortino(returns: list[float], periods: int = 252) -> float:
    if not returns:
        return 0.0
    downside = [min(value, 0.0) for value in returns]
    downside_deviation = math.sqrt(
        sum(value * value for value in downside) / len(downside)
    )
    if downside_deviation == 0:
        return 0.0
    return statistics.mean(returns) / downside_deviation * math.sqrt(periods)


def trade_statistics(trades: list[dict[str, Any]]) -> dict[str, float]:
    pnls = [float(trade.get("net_pnl", 0.0)) for trade in trades]
    wins = [value for value in pnls if value > 0]
    losses = [value for value in pnls if value < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    total = len(pnls)

    return {
        "total_trades": total,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate_pct": round(len(wins) / total * 100.0, 4) if total else 0.0,
        "loss_rate_pct": round(len(losses) / total * 100.0, 4) if total else 0.0,
        "average_win": round(sum(wins) / len(wins), 4) if wins else 0.0,
        "average_loss": round(sum(losses) / len(losses), 4) if losses else 0.0,
        "gross_profit": round(gross_profit, 4),
        "gross_loss": round(gross_loss, 4),
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss else (
            999.0 if gross_profit > 0 else 0.0
        ),
        "expectancy": round(sum(pnls) / total, 4) if total else 0.0,
    }
