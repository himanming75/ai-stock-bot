from __future__ import annotations
from typing import Any

def portfolio_heat(
    risk_allocations: list[dict[str, Any]],
    exposure_control: dict[str, Any],
) -> dict[str, Any]:
    total=sum(float(row.get("risk_budget_pct",0.0)) for row in risk_allocations)
    multiplier=float(exposure_control.get("final_exposure_multiplier",0.0))
    heat=total*multiplier
    return {
        "gross_risk_budget_pct":round(total,6),
        "exposure_multiplier":round(multiplier,6),
        "portfolio_heat_pct":round(heat,6),
    }
