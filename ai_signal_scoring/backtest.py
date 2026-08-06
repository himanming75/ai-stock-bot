from __future__ import annotations
import math


def _drawdown(equity: list[float]) -> float:
    peak = equity[0] if equity else 1.0
    maximum = 0.0
    for value in equity:
        peak = max(peak, value)
        if peak:
            maximum = max(maximum, (peak - value) / peak)
    return maximum


def backtest_bridge(
    *,
    prices: list[float],
    actions: list[str],
    initial_equity: float = 10000.0,
) -> dict:
    if len(prices) != len(actions):
        raise ValueError("PRICE_ACTION_LENGTH_MISMATCH")
    if len(prices) < 3:
        raise ValueError("MINIMUM_3_BACKTEST_POINTS")

    returns = []
    equity = [float(initial_equity)]
    wins = 0
    losses = 0
    gross_profit = 0.0
    gross_loss = 0.0

    for i in range(len(prices) - 1):
        current = float(prices[i])
        following = float(prices[i + 1])
        movement = 0.0 if current == 0 else (following / current - 1)
        action = actions[i]
        if action == "BUY":
            strategy_return = movement
        elif action == "SELL":
            strategy_return = -movement
        else:
            strategy_return = 0.0

        returns.append(strategy_return)
        equity.append(equity[-1] * (1 + strategy_return))
        if strategy_return > 0:
            wins += 1
            gross_profit += strategy_return
        elif strategy_return < 0:
            losses += 1
            gross_loss += abs(strategy_return)

    trades = wins + losses
    win_rate = 0.0 if trades == 0 else wins / trades
    profit_factor = (
        None if gross_loss == 0
        else gross_profit / gross_loss
    )
    average = sum(returns) / len(returns)
    variance = sum((r - average) ** 2 for r in returns) / len(returns)
    std = math.sqrt(variance)
    sharpe = 0.0 if std == 0 else average / std * math.sqrt(252)
    total_return = equity[-1] / initial_equity - 1

    return {
        "status": "PASS",
        "mode": "OFFLINE_BRIDGE_ONLY",
        "initial_equity": initial_equity,
        "ending_equity": round(equity[-1], 2),
        "total_return_percent": round(total_return * 100, 4),
        "win_rate_percent": round(win_rate * 100, 2),
        "profit_factor": (
            None if profit_factor is None else round(profit_factor, 4)
        ),
        "max_drawdown_percent": round(_drawdown(equity) * 100, 4),
        "sharpe_candidate": round(sharpe, 4),
        "trade_count": trades,
        "live_execution_enabled": False,
        "order_submission_enabled": False,
    }
