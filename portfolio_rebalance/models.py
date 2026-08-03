from __future__ import annotations
from typing import Any

def target_weights(portfolio_result: dict[str, Any]) -> dict[str, float]:
    output = {}
    for row in portfolio_result.get("allocation", {}).get("allocations", []):
        strategy_id = str(row.get("strategy_id", ""))
        if not strategy_id:
            continue
        output[strategy_id] = float(row.get("target_weight_pct", 0.0))
    output["CASH"] = float(
        portfolio_result.get("allocation", {}).get("cash_weight_pct", 0.0)
    )
    return output

def current_weights(
    account_equity: float,
    cash: float,
    strategy_positions: list[dict[str, Any]],
) -> dict[str, float]:
    output = {}
    denominator = account_equity if account_equity > 0 else 1.0
    for row in strategy_positions:
        strategy_id = str(row.get("strategy_id", ""))
        if not strategy_id:
            continue
        output[strategy_id] = (
            float(row.get("market_value", 0.0)) / denominator * 100.0
        )
    output["CASH"] = cash / denominator * 100.0
    return output

def merge_weight_rows(
    targets: dict[str, float],
    currents: dict[str, float],
) -> list[dict[str, Any]]:
    rows = []
    for strategy_id in sorted(set(targets) | set(currents)):
        target = float(targets.get(strategy_id, 0.0))
        current = float(currents.get(strategy_id, 0.0))
        rows.append({
            "strategy_id": strategy_id,
            "target_weight_pct": round(target, 6),
            "current_weight_pct": round(current, 6),
            "weight_gap_pct": round(target - current, 6),
        })
    return rows
