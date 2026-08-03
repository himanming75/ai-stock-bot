from __future__ import annotations

import hashlib
import json
from typing import Any

from backtest_v2.engine import run_backtest
from backtest_v2.models import Bar
from multi_asset_backtest.benchmark import buy_and_hold
from multi_asset_backtest.correlation import correlation_matrix
from multi_asset_backtest.portfolio import (
    combine_equity_curves,
    concentration_metrics,
    sector_performance,
)


def digest_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def run_multi_asset_backtest(
    assets: list[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    total_initial_cash = float(policy.get("total_initial_cash", 100000.0))
    backtest_policy = dict(policy.get("backtest_policy", {}))

    enabled = [asset for asset in assets if asset.get("enabled", True)]
    if not enabled:
        raise ValueError("at least one enabled asset is required")

    raw_weights = {
        str(asset["symbol"]).upper(): float(asset.get("weight", 0.0))
        for asset in enabled
    }
    total_weight = sum(max(0.0, value) for value in raw_weights.values())
    if total_weight <= 0:
        equal = 1.0 / len(enabled)
        weights = {str(asset["symbol"]).upper(): equal for asset in enabled}
    else:
        weights = {
            symbol: max(0.0, value) / total_weight
            for symbol, value in raw_weights.items()
        }

    results = []
    benchmarks = []
    sectors = {}
    close_series = {}

    for asset in enabled:
        symbol = str(asset["symbol"]).upper()
        sector = str(asset.get("sector", "UNKNOWN")).upper()
        bars = [
            Bar.from_dict(row)
            for row in asset.get("bars", [])
            if isinstance(row, dict)
        ]
        if not bars:
            raise ValueError(f"no bars for {symbol}")

        allocated_cash = total_initial_cash * weights[symbol]
        local_policy = {
            **backtest_policy,
            "initial_cash": allocated_cash,
        }
        result = run_backtest(symbol, bars, local_policy)
        benchmark = buy_and_hold(bars, allocated_cash)

        results.append(result)
        benchmarks.append({
            "symbol": symbol,
            **benchmark,
        })
        sectors[symbol] = sector
        close_series[symbol] = [bar.close for bar in bars]

    portfolio = combine_equity_curves(
        results,
        weights,
        total_initial_cash,
    )
    benchmark_ending = sum(row["ending_equity"] for row in benchmarks)
    benchmark_return = (
        (benchmark_ending - total_initial_cash) / total_initial_cash * 100.0
        if total_initial_cash
        else 0.0
    )
    excess_return = portfolio["total_return_pct"] - benchmark_return

    per_asset = []
    for result, benchmark in zip(results, benchmarks):
        per_asset.append({
            "symbol": result["symbol"],
            "sector": sectors[result["symbol"]],
            "weight_pct": round(weights[result["symbol"]] * 100.0, 4),
            "strategy_return_pct": result["total_return_pct"],
            "benchmark_return_pct": benchmark["total_return_pct"],
            "excess_return_pct": round(
                result["total_return_pct"] - benchmark["total_return_pct"],
                4,
            ),
            "maximum_drawdown_pct": result["maximum_drawdown_pct"],
            "total_trades": result["trade_statistics"]["total_trades"],
            "win_rate_pct": result["trade_statistics"]["win_rate_pct"],
            "equity_curve": result["equity_curve"],
        })

    correlations = correlation_matrix(close_series)
    concentration = concentration_metrics(weights)
    sectors_summary = sector_performance(results, sectors)

    checks = {
        "minimum_asset_count": len(per_asset) >= int(
            policy.get("minimum_asset_count", 3)
        ),
        "portfolio_equity_positive": portfolio["ending_equity"] > 0,
        "benchmark_available": benchmark_ending > 0,
        "concentration_cap": concentration["largest_weight_pct"] <= float(
            policy.get("maximum_asset_weight_pct", 50.0)
        ),
        "effective_asset_count": concentration["effective_asset_count"] >= float(
            policy.get("minimum_effective_asset_count", 2.0)
        ),
    }
    certified = all(checks.values())

    certificate_body = {
        "state": (
            "MULTI_ASSET_BACKTEST_CERTIFIED"
            if certified
            else "MULTI_ASSET_BACKTEST_REVIEW_REQUIRED"
        ),
        "asset_count": len(per_asset),
        "portfolio_return_pct": portfolio["total_return_pct"],
        "benchmark_return_pct": round(benchmark_return, 4),
        "excess_return_pct": round(excess_return, 4),
        "checks": checks,
        "paper_only": True,
    }
    certificate = {
        **certificate_body,
        "certificate_sha256": digest_payload(certificate_body),
    }

    return {
        "asset_count": len(per_asset),
        "weights": {
            symbol: round(value * 100.0, 4)
            for symbol, value in sorted(weights.items())
        },
        "per_asset": per_asset,
        "portfolio": portfolio,
        "benchmark": {
            "ending_equity": round(benchmark_ending, 4),
            "total_return_pct": round(benchmark_return, 4),
        },
        "excess_return_pct": round(excess_return, 4),
        "sector_performance": sectors_summary,
        "correlation_matrix": correlations,
        "concentration": concentration,
        "checks": checks,
        "certified": certified,
        "certificate": certificate,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
    }
