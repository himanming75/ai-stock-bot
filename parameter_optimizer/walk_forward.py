from __future__ import annotations
from typing import Any
from v89_engine.backtest import run_strategy

def split_windows(bars: list[dict[str, Any]], window_count: int = 4) -> list[list[dict[str, Any]]]:
    if window_count <= 0 or len(bars) < window_count:
        return []
    size = len(bars) // window_count
    windows = []
    for index in range(window_count):
        start = index * size
        end = len(bars) if index == window_count - 1 else (index + 1) * size
        window = bars[start:end]
        if len(window) >= 20:
            windows.append(window)
    return windows

def evaluate_windows(
    bars: list[dict[str, Any]],
    strategy: str,
    parameters: dict[str, Any],
    window_count: int = 4,
) -> dict[str, Any]:
    windows = split_windows(bars, window_count)
    results = [
        run_strategy(window, strategy, parameters)
        for window in windows
    ]
    positive = [row for row in results if row["total_return_pct"] > 0]
    returns = [row["total_return_pct"] for row in results]
    drawdowns = [row["maximum_drawdown_pct"] for row in results]
    sharpes = [row["sharpe_ratio"] for row in results]
    trades = [row["total_trades"] for row in results]

    return {
        "window_count": len(results),
        "positive_window_count": len(positive),
        "positive_window_pct": (
            round(len(positive) / len(results) * 100.0, 4)
            if results else 0.0
        ),
        "average_return_pct": round(sum(returns) / len(returns), 4) if returns else 0.0,
        "worst_return_pct": round(min(returns), 4) if returns else 0.0,
        "best_return_pct": round(max(returns), 4) if returns else 0.0,
        "average_drawdown_pct": round(sum(drawdowns) / len(drawdowns), 4) if drawdowns else 0.0,
        "worst_drawdown_pct": round(max(drawdowns), 4) if drawdowns else 0.0,
        "average_sharpe": round(sum(sharpes) / len(sharpes), 4) if sharpes else 0.0,
        "total_window_trades": sum(trades),
        "window_results": results,
    }
