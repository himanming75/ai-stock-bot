from __future__ import annotations

from collections import defaultdict
from typing import Any


def combine_equity_curves(
    results: list[dict[str, Any]],
    weights: dict[str, float],
    total_initial_cash: float,
) -> dict[str, Any]:
    if not results:
        return {
            "equity_curve": [],
            "ending_equity": total_initial_cash,
            "total_return_pct": 0.0,
        }

    min_length = min(len(row["equity_curve"]) for row in results)
    curve = []
    for index in range(min_length):
        equity = 0.0
        for row in results:
            symbol = row["symbol"]
            weight = float(weights.get(symbol, 0.0))
            allocated = total_initial_cash * weight
            normalized = (
                row["equity_curve"][index] / row["initial_cash"]
                if row["initial_cash"]
                else 1.0
            )
            equity += allocated * normalized
        curve.append(equity)

    ending = curve[-1] if curve else total_initial_cash
    total_return = (
        (ending - total_initial_cash) / total_initial_cash * 100.0
        if total_initial_cash
        else 0.0
    )
    return {
        "equity_curve": [round(value, 4) for value in curve],
        "ending_equity": round(ending, 4),
        "total_return_pct": round(total_return, 4),
    }


def sector_performance(
    asset_results: list[dict[str, Any]],
    sectors: dict[str, str],
) -> dict[str, Any]:
    grouped = defaultdict(list)
    for result in asset_results:
        grouped[sectors.get(result["symbol"], "UNKNOWN")].append(
            float(result["total_return_pct"])
        )

    return {
        sector: {
            "asset_count": len(values),
            "average_return_pct": round(sum(values) / len(values), 4),
            "best_return_pct": round(max(values), 4),
            "worst_return_pct": round(min(values), 4),
        }
        for sector, values in sorted(grouped.items())
    }


def concentration_metrics(weights: dict[str, float]) -> dict[str, float]:
    values = [max(0.0, float(value)) for value in weights.values()]
    total = sum(values)
    if total <= 0:
        return {
            "largest_weight_pct": 0.0,
            "herfindahl_index": 0.0,
            "effective_asset_count": 0.0,
        }
    normalized = [value / total for value in values]
    hhi = sum(value * value for value in normalized)
    return {
        "largest_weight_pct": round(max(normalized) * 100.0, 4),
        "herfindahl_index": round(hhi, 6),
        "effective_asset_count": round(1.0 / hhi, 4) if hhi else 0.0,
    }
