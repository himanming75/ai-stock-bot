from __future__ import annotations
from typing import Any

def calculate(trades: list[dict[str, Any]], equity_curve: list[float]) -> dict[str, Any]:
    wins = [float(x.get("pnl", 0) or 0) for x in trades if float(x.get("pnl", 0) or 0) > 0]
    losses = [float(x.get("pnl", 0) or 0) for x in trades if float(x.get("pnl", 0) or 0) < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    win_rate = len(wins) / len(trades) * 100 if trades else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss else (999.0 if gross_profit else 0.0)
    peak = None
    maximum_drawdown = 0.0
    for value in equity_curve:
        peak = value if peak is None else max(peak, value)
        drawdown = (peak - value) / peak * 100 if peak else 0.0
        maximum_drawdown = max(maximum_drawdown, drawdown)
    return {
        "trade_count": len(trades),
        "win_rate_pct": round(win_rate, 4),
        "profit_factor": round(profit_factor, 4),
        "maximum_drawdown_pct": round(maximum_drawdown, 4),
        "net_pnl": round(sum(float(x.get("pnl", 0) or 0) for x in trades), 2),
    }
