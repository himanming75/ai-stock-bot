from __future__ import annotations
from typing import Any

def allocate(candidate:dict[str,Any],sizing:dict[str,Any],policy:dict[str,Any])->dict[str,Any]:
    strategy=str(candidate.get("source_strategy_id","UNKNOWN"))
    symbol=str(candidate.get("symbol",""))
    strategy_cap=float(policy.get("strategy_risk_budget_pct",{}).get(strategy,policy.get("default_strategy_risk_budget_pct",0.5)))
    symbol_cap=float(policy.get("symbol_risk_budget_pct",{}).get(symbol,policy.get("default_symbol_risk_budget_pct",0.5)))
    requested=float(sizing.get("adjusted_risk_amount",0.0))
    equity=float(sizing.get("equity",0.0))
    strategy_budget=equity*strategy_cap/100.0
    symbol_budget=equity*symbol_cap/100.0
    approved=min(requested,strategy_budget,symbol_budget)
    return {
        "strategy_id":strategy,
        "symbol":symbol,
        "requested_risk_amount":round(requested,2),
        "strategy_budget_amount":round(strategy_budget,2),
        "symbol_budget_amount":round(symbol_budget,2),
        "approved_risk_amount":round(approved,2),
        "budget_passed":approved>0 and requested<=strategy_budget and requested<=symbol_budget,
    }
