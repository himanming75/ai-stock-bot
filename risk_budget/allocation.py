from __future__ import annotations
from typing import Any
from risk_budget.kelly import fractional_kelly
from risk_budget.volatility import volatility_scale

def allocate_risk_budgets(
    candidates: list[dict[str, Any]],
    portfolio_risk: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    total_risk_budget_pct=float(policy.get("total_risk_budget_pct",10.0))
    maximum_strategy_budget_pct=float(
        policy.get("maximum_strategy_risk_budget_pct",5.0)
    )
    minimum_strategy_budget_pct=float(
        policy.get("minimum_strategy_risk_budget_pct",0.25)
    )
    target_volatility_pct=float(policy.get("target_strategy_volatility_pct",2.0))
    kelly_fraction=float(policy.get("kelly_fraction",0.25))
    maximum_kelly=float(policy.get("maximum_kelly_fraction",0.5))
    minimum_multiplier=float(policy.get("minimum_exposure_multiplier",0.25))
    maximum_multiplier=float(policy.get("maximum_exposure_multiplier",1.25))

    risk_score=float(portfolio_risk.get("risk_score",{}).get("risk_score",100.0))
    risk_headroom=max(0.0,1.0-risk_score/100.0)

    rows=[]
    raw_total=0.0
    for candidate in candidates:
        kelly=fractional_kelly(
            candidate["win_rate_pct"],
            candidate["average_win_pct"],
            candidate["average_loss_pct"],
            kelly_fraction,
            maximum_kelly,
        )
        vol=volatility_scale(
            target_volatility_pct,
            candidate["observed_volatility_pct"],
            minimum_multiplier,
            maximum_multiplier,
        )
        quality=max(0.0,min(1.0,candidate["risk_quality_score"]/100.0))
        raw=max(
            0.0,
            candidate["target_weight_pct"]/100.0
            * kelly["applied_kelly_fraction"]
            * vol["applied_multiplier"]
            * quality
            * risk_headroom
        )
        raw_total+=raw
        rows.append({
            **candidate,
            "kelly":kelly,
            "volatility_scale":vol,
            "raw_risk_weight":raw,
        })

    allocations=[]
    if raw_total>0:
        for row in rows:
            budget=total_risk_budget_pct*row["raw_risk_weight"]/raw_total
            budget=max(
                minimum_strategy_budget_pct,
                min(maximum_strategy_budget_pct,budget),
            )
            allocations.append({
                "strategy_id":row["strategy_id"],
                "target_weight_pct":round(row["target_weight_pct"],6),
                "risk_budget_pct":round(budget,6),
                "kelly_fraction":row["kelly"]["applied_kelly_fraction"],
                "volatility_multiplier":row["volatility_scale"]["applied_multiplier"],
                "risk_quality_score":round(row["risk_quality_score"],6),
            })

    used=sum(row["risk_budget_pct"] for row in allocations)
    if used>total_risk_budget_pct and used>0:
        scale=total_risk_budget_pct/used
        for row in allocations:
            row["risk_budget_pct"]=round(row["risk_budget_pct"]*scale,6)
        used=sum(row["risk_budget_pct"] for row in allocations)

    return {
        "total_risk_budget_pct":round(total_risk_budget_pct,6),
        "used_risk_budget_pct":round(used,6),
        "unused_risk_budget_pct":round(max(0.0,total_risk_budget_pct-used),6),
        "portfolio_risk_headroom":round(risk_headroom,6),
        "allocations":allocations,
    }
