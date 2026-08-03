from __future__ import annotations
from pathlib import Path
from typing import Any

from automated_backtest.data import load_bars, slice_bars
from automated_backtest.strategies import signals

def maximum_drawdown(equity: list[float]) -> float:
    peak = equity[0] if equity else 0.0
    worst = 0.0
    for value in equity:
        peak = max(peak, value)
        if peak > 0:
            worst = max(worst, (peak - value) / peak)
    return worst * 100.0

def run_job(job: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    if not job.get("dataset_exists"):
        return {
            **job,
            "state": "SKIPPED_DATASET_MISSING",
            "status": "PASS",
        }

    bars = load_bars(Path(job["dataset_path"]))
    bars = slice_bars(bars, job["start_index"], job["end_index"])
    minimum_bars = int(policy.get("minimum_bars", 30))
    if len(bars) < minimum_bars:
        return {
            **job,
            "state": "SKIPPED_INSUFFICIENT_BARS",
            "status": "PASS",
            "bar_count": len(bars),
        }

    closes = [row["close"] for row in bars]
    signal_values = signals(job["family"], closes, job["parameters"])
    starting_equity = float(policy.get("starting_equity", 100000.0))
    commission_bps = float(policy.get("commission_bps", 0.0))
    slippage_bps = float(policy.get("slippage_bps", 0.0))
    equity = [starting_equity]
    trade_count = 0
    wins = 0

    for i in range(1, len(closes)):
        exposure = signal_values[i-1]
        raw_return = closes[i] / closes[i-1] - 1.0
        cost = 0.0
        if signal_values[i] != signal_values[i-1]:
            trade_count += 1
            cost = (commission_bps + slippage_bps) / 10000.0
        strategy_return = exposure * raw_return - cost
        equity.append(equity[-1] * (1.0 + strategy_return))
        if strategy_return > 0:
            wins += 1

    ending = equity[-1]
    total_return = (ending / starting_equity - 1.0) * 100.0
    positive_periods = wins
    active_periods = max(1, sum(1 for value in signal_values[:-1] if value))
    win_rate = positive_periods / active_periods * 100.0

    return {
        **job,
        "state": "COMPLETED",
        "status": "PASS",
        "bar_count": len(bars),
        "starting_equity": round(starting_equity, 4),
        "ending_equity": round(ending, 4),
        "total_return_pct": round(total_return, 6),
        "maximum_drawdown_pct": round(maximum_drawdown(equity), 6),
        "trade_count": trade_count,
        "win_rate_pct": round(win_rate, 6),
    }
