from __future__ import annotations
from typing import Any

def dynamic_exposure_control(
    allocation: dict[str, Any],
    portfolio_result: dict[str, Any],
    risk_result: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    maximum_gross=float(policy.get("maximum_gross_exposure_pct",100.0))
    minimum_gross=float(policy.get("minimum_gross_exposure_pct",20.0))
    current_gross=float(
        risk_result.get("exposure",{}).get("gross_exposure_pct",0.0)
    )
    risk_score=float(
        risk_result.get("risk_score",{}).get("risk_score",100.0)
    )
    stress_loss=float(
        risk_result.get("stress",{}).get("worst_estimated_loss_pct",100.0)
    )
    risk_multiplier=max(0.25,1.0-risk_score/120.0)
    stress_multiplier=max(0.25,1.0-stress_loss/50.0)
    budget_utilization=(
        allocation.get("used_risk_budget_pct",0.0)
        / max(1e-9,allocation.get("total_risk_budget_pct",1.0))
    )
    budget_multiplier=max(0.25,min(1.0,budget_utilization))
    final_multiplier=min(risk_multiplier,stress_multiplier,budget_multiplier)
    target_gross=max(
        minimum_gross,
        min(maximum_gross,current_gross*final_multiplier),
    )
    return {
        "current_gross_exposure_pct":round(current_gross,6),
        "risk_multiplier":round(risk_multiplier,6),
        "stress_multiplier":round(stress_multiplier,6),
        "budget_multiplier":round(budget_multiplier,6),
        "final_exposure_multiplier":round(final_multiplier,6),
        "target_gross_exposure_pct":round(target_gross,6),
    }
