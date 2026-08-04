from __future__ import annotations
from typing import Any

def evaluate(
    account:dict[str,Any],
    positions:list[dict[str,Any]],
    sizing:dict[str,Any],
    policy:dict[str,Any],
)->dict[str,Any]:
    equity=float(account.get("equity",0.0))
    cash=float(account.get("cash",0.0))
    existing=sum(abs(float(p.get("market_value",0.0))) for p in positions)
    proposed=float(sizing.get("final_notional",0.0))
    gross=existing+proposed
    gross_pct=(gross/equity*100.0) if equity else 0.0
    cash_after=cash-proposed
    cash_after_pct=(cash_after/equity*100.0) if equity else 0.0
    checks={
        "gross_exposure_within_limit":gross_pct<=float(policy.get("maximum_gross_exposure_pct",25.0)),
        "minimum_cash_preserved":cash_after_pct>=float(policy.get("minimum_cash_pct",50.0)),
        "proposed_order_within_limit":proposed<=float(policy.get("maximum_order_notional",250.0)),
        "equity_positive":equity>0,
    }
    failed=[k for k,v in checks.items() if not v]
    return {
        "existing_gross_exposure":round(existing,2),
        "proposed_notional":round(proposed,2),
        "projected_gross_exposure":round(gross,2),
        "projected_gross_exposure_pct":round(gross_pct,6),
        "projected_cash":round(cash_after,2),
        "projected_cash_pct":round(cash_after_pct,6),
        "checks":checks,
        "failed":failed,
        "passed":not failed,
    }
