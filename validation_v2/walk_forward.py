from __future__ import annotations

from typing import Any

from backtest_v2.engine import run_backtest
from backtest_v2.models import Bar


def run_walk_forward(
    symbol: str,
    bars: list[Bar],
    policy: dict[str, Any],
) -> dict[str, Any]:
    train_size = int(policy.get("train_size", 100))
    test_size = int(policy.get("test_size", 40))
    step_size = int(policy.get("step_size", test_size))

    windows = []
    start = 0
    while start + train_size + test_size <= len(bars):
        train = bars[start:start + train_size]
        test = bars[start + train_size:start + train_size + test_size]
        result = run_backtest(symbol, test, policy.get("backtest_policy", {}))
        windows.append({
            "window": len(windows) + 1,
            "train_start": train[0].timestamp,
            "train_end": train[-1].timestamp,
            "test_start": test[0].timestamp,
            "test_end": test[-1].timestamp,
            "test_return_pct": result["total_return_pct"],
            "test_max_drawdown_pct": result["maximum_drawdown_pct"],
            "test_total_trades": result["trade_statistics"]["total_trades"],
            "test_win_rate_pct": result["trade_statistics"]["win_rate_pct"],
        })
        start += step_size

    returns = [float(row["test_return_pct"]) for row in windows]
    positive = [value for value in returns if value > 0]
    consistency = len(positive) / len(returns) * 100.0 if returns else 0.0

    return {
        "window_count": len(windows),
        "windows": windows,
        "average_test_return_pct": round(
            sum(returns) / len(returns), 4
        ) if returns else 0.0,
        "median_test_return_pct": round(
            sorted(returns)[len(returns)//2], 4
        ) if returns else 0.0,
        "positive_window_pct": round(consistency, 2),
        "minimum_test_return_pct": round(min(returns), 4) if returns else 0.0,
        "maximum_test_return_pct": round(max(returns), 4) if returns else 0.0,
    }
