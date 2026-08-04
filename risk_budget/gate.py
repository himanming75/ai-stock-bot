from __future__ import annotations
from typing import Any

def evaluate_gate(
    allocation: dict[str, Any],
    exposure: dict[str, Any],
    heat: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    rows=allocation.get("allocations",[])
    largest=max(
        [float(row.get("risk_budget_pct",0.0)) for row in rows] or [0.0]
    )
    checks={
        "risk_allocations_present":bool(rows),
        "total_budget_limit":(
            float(allocation.get("used_risk_budget_pct",0.0))
            <= float(allocation.get("total_risk_budget_pct",0.0))+1e-6
        ),
        "single_strategy_budget_limit":(
            largest<=float(policy.get("maximum_strategy_risk_budget_pct",5.0))+1e-6
        ),
        "portfolio_heat_limit":(
            float(heat.get("portfolio_heat_pct",0.0))
            <= float(policy.get("maximum_portfolio_heat_pct",10.0))
        ),
        "gross_exposure_limit":(
            float(exposure.get("target_gross_exposure_pct",0.0))
            <= float(policy.get("maximum_gross_exposure_pct",100.0))
        ),
        "exposure_multiplier_valid":(
            0.0<float(exposure.get("final_exposure_multiplier",0.0))<=1.25
        ),
    }
    failed=[name for name,passed in checks.items() if not passed]
    return {
        "passed":not failed,
        "checks":checks,
        "failed":failed,
        "largest_strategy_risk_budget_pct":round(largest,6),
    }
