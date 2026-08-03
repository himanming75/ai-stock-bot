from __future__ import annotations

from copy import deepcopy
from typing import Any

from backtest_v2.engine import run_backtest
from backtest_v2.models import Bar


def mutate_bars(bars: list[Bar], scenario: str) -> list[Bar]:
    output = []
    for index, bar in enumerate(bars):
        if scenario == "gap_down" and index == len(bars) // 2:
            factor = 0.88
            output.append(Bar(
                timestamp=bar.timestamp,
                open=bar.open * factor,
                high=bar.high * factor,
                low=bar.low * factor,
                close=bar.close * factor,
                volume=bar.volume * 1.5,
            ))
        elif scenario == "flash_crash" and index == len(bars) // 2:
            output.append(Bar(
                timestamp=bar.timestamp,
                open=bar.open,
                high=bar.high,
                low=bar.low * 0.75,
                close=bar.close * 0.82,
                volume=bar.volume * 2.0,
            ))
        elif scenario == "missing_data" and index % 17 == 0:
            continue
        else:
            output.append(bar)
    return output


def run_stress_tests(
    symbol: str,
    bars: list[Bar],
    policy: dict[str, Any],
) -> dict[str, Any]:
    base_policy = dict(policy.get("backtest_policy", {}))
    scenarios = []

    for name, changes in (
        ("double_costs", {"commission_bps": base_policy.get("commission_bps", 1) * 2,
                          "slippage_bps": base_policy.get("slippage_bps", 2) * 2}),
        ("triple_costs", {"commission_bps": base_policy.get("commission_bps", 1) * 3,
                          "slippage_bps": base_policy.get("slippage_bps", 2) * 3}),
    ):
        scenario_policy = dict(base_policy)
        scenario_policy.update(changes)
        result = run_backtest(symbol, bars, scenario_policy)
        scenarios.append({
            "scenario": name,
            "total_return_pct": result["total_return_pct"],
            "maximum_drawdown_pct": result["maximum_drawdown_pct"],
            "total_trades": result["trade_statistics"]["total_trades"],
        })

    for name in ("gap_down", "flash_crash", "missing_data"):
        mutated = mutate_bars(bars, name)
        result = run_backtest(symbol, mutated, base_policy)
        scenarios.append({
            "scenario": name,
            "total_return_pct": result["total_return_pct"],
            "maximum_drawdown_pct": result["maximum_drawdown_pct"],
            "total_trades": result["trade_statistics"]["total_trades"],
            "bar_count": len(mutated),
        })

    return {
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
        "worst_return_pct": round(
            min(row["total_return_pct"] for row in scenarios), 4
        ) if scenarios else 0.0,
        "worst_drawdown_pct": round(
            max(row["maximum_drawdown_pct"] for row in scenarios), 4
        ) if scenarios else 0.0,
    }
