from __future__ import annotations
from typing import Any

def calculate_exposure(
    portfolio_result: dict[str, Any],
    rebalance_result: dict[str, Any],
) -> dict[str, Any]:
    allocations=portfolio_result.get("allocation",{}).get("allocations",[])
    gross=sum(float(row.get("target_weight_pct",0.0)) for row in allocations)
    cash=float(portfolio_result.get("allocation",{}).get("cash_weight_pct",0.0))
    largest=max(
        [float(row.get("target_weight_pct",0.0)) for row in allocations] or [0.0]
    )
    turnover=float(
        rebalance_result.get("turnover",{}).get("used_turnover_pct",0.0)
    )
    return {
        "gross_exposure_pct":round(gross,6),
        "net_exposure_pct":round(gross,6),
        "cash_weight_pct":round(cash,6),
        "largest_strategy_weight_pct":round(largest,6),
        "turnover_pct":round(turnover,6),
        "strategy_count":len(allocations),
    }
