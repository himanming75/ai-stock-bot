from __future__ import annotations
from typing import Any

def stress_test(
    account_equity: float,
    exposure: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    shocks=policy.get("stress_scenarios",[])
    rows=[]
    worst_loss=0.0
    for row in shocks:
        shock_pct=float(row.get("market_shock_pct",0.0))
        multiplier=float(row.get("exposure_multiplier",1.0))
        gross=float(exposure.get("gross_exposure_pct",0.0))/100.0
        loss_amount=account_equity*gross*abs(shock_pct)/100.0*multiplier
        worst_loss=max(worst_loss,loss_amount)
        rows.append({
            "scenario_id":str(row.get("scenario_id")),
            "market_shock_pct":shock_pct,
            "exposure_multiplier":multiplier,
            "estimated_loss_amount":round(loss_amount,6),
            "estimated_loss_pct":round(
                loss_amount/account_equity*100.0 if account_equity else 0.0,
                6,
            ),
        })
    return {
        "scenario_count":len(rows),
        "scenarios":rows,
        "worst_estimated_loss_amount":round(worst_loss,6),
        "worst_estimated_loss_pct":round(
            worst_loss/account_equity*100.0 if account_equity else 0.0,
            6,
        ),
    }
