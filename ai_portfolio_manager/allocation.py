from __future__ import annotations
from typing import Any

def _normalize(weights: dict[str,float], total: float) -> dict[str,float]:
    current=sum(weights.values())
    if current<=0:
        return {key:0.0 for key in weights}
    return {key:value/current*total for key,value in weights.items()}

def allocate(
    rankings: list[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    minimum_score=float(policy.get("minimum_portfolio_score",-999999.0))
    maximum_strategies=int(policy.get("maximum_strategy_count",5))
    minimum_cash_pct=float(policy.get("minimum_cash_pct",10.0))
    maximum_weight_pct=float(policy.get("maximum_strategy_weight_pct",40.0))
    minimum_weight_pct=float(policy.get("minimum_strategy_weight_pct",5.0))

    eligible=[
        row for row in rankings
        if float(row.get("portfolio_score",0.0))>=minimum_score
    ][:maximum_strategies]

    investable_limit=max(0.0,100.0-minimum_cash_pct)
    raw={
        row["strategy_id"]:max(0.0,float(row.get("portfolio_score",0.0)))
        for row in eligible
    }
    if eligible and sum(raw.values())<=0:
        raw={row["strategy_id"]:1.0 for row in eligible}

    proposed=_normalize(raw,investable_limit)
    weights={key:min(value,maximum_weight_pct) for key,value in proposed.items()}

    # Redistribute only to strategies that still have room, never above the cap.
    for _ in range(20):
        remaining=investable_limit-sum(weights.values())
        if remaining<=1e-9:
            break
        room={
            key:max(0.0,maximum_weight_pct-value)
            for key,value in weights.items()
            if value<maximum_weight_pct-1e-9
        }
        if not room:
            break
        room_total=sum(room.values())
        if room_total<=0:
            break
        distributed=0.0
        for key,available in room.items():
            addition=min(available,remaining*(available/room_total))
            weights[key]+=addition
            distributed+=addition
        if distributed<=1e-9:
            break

    # Drop insignificant allocations without renormalizing above the cap.
    weights={
        key:value for key,value in weights.items()
        if value>=minimum_weight_pct
    }
    allocations=[
        {"strategy_id":key,"target_weight_pct":round(value,6)}
        for key,value in sorted(
            weights.items(),key=lambda item:item[1],reverse=True
        )
    ]
    used=sum(row["target_weight_pct"] for row in allocations)
    cash_pct=round(100.0-used,6)
    return {
        "eligible_strategy_count":len(eligible),
        "allocated_strategy_count":len(allocations),
        "allocations":allocations,
        "cash_weight_pct":cash_pct,
        "invested_weight_pct":round(used,6),
        "unallocated_due_to_caps_pct":round(
            max(0.0,investable_limit-used),6
        ),
    }
