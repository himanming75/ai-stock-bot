from __future__ import annotations
from typing import Any

def evaluate_risk(
    allocation: dict[str, Any],
    rankings: list[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    allocations=allocation.get("allocations",[])
    largest=max(
        [float(row.get("target_weight_pct",0.0)) for row in allocations]
        or [0.0]
    )
    cash=float(allocation.get("cash_weight_pct",0.0))
    lookup={row["strategy_id"]:row for row in rankings}
    weighted_drawdown=0.0
    for row in allocations:
        candidate=lookup.get(row["strategy_id"],{})
        weighted_drawdown+=(
            float(row["target_weight_pct"])/100.0
            * float(candidate.get("worst_drawdown_pct",0.0))
        )
    checks={
        "minimum_strategy_count":len(allocations)>=int(policy.get("minimum_strategy_count",2)),
        "maximum_single_weight":largest<=float(policy.get("maximum_strategy_weight_pct",40.0))+1e-9,
        "minimum_cash":cash>=float(policy.get("minimum_cash_pct",10.0))-1e-9,
        "weights_sum_to_100":abs(
            sum(float(r["target_weight_pct"]) for r in allocations)+cash-100.0
        )<=0.001,
        "weighted_drawdown_limit":weighted_drawdown<=float(policy.get("maximum_weighted_drawdown_pct",15.0)),
    }
    failed=[name for name,passed in checks.items() if not passed]
    return {
        "passed":not failed,
        "checks":checks,
        "failed":failed,
        "largest_strategy_weight_pct":round(largest,6),
        "cash_weight_pct":round(cash,6),
        "weighted_drawdown_pct":round(weighted_drawdown,6),
    }
