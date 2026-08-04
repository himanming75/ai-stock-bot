from __future__ import annotations
from typing import Any

def calculate(candidate:dict[str,Any],account:dict[str,Any],policy:dict[str,Any])->dict[str,Any]:
    equity=float(account.get("equity",0.0))
    price=float(candidate.get("reference_price",candidate.get("estimated_price",0.0)) or 0.0)
    stop_pct=max(float(candidate.get("stop_distance_pct",policy.get("default_stop_distance_pct",2.0))),0.01)
    volatility=max(float(candidate.get("volatility_pct",policy.get("default_volatility_pct",1.5))),0.01)
    base_risk_amount=equity*float(policy.get("risk_per_trade_pct",0.25))/100.0
    volatility_multiplier=min(1.0,float(policy.get("target_volatility_pct",1.5))/volatility)
    adjusted_risk_amount=base_risk_amount*volatility_multiplier
    risk_per_share=price*stop_pct/100.0
    raw_qty=int(adjusted_risk_amount//risk_per_share) if risk_per_share>0 else 0
    max_qty=int(policy.get("maximum_quantity",1))
    max_notional=float(policy.get("maximum_order_notional",250.0))
    notional_qty=int(max_notional//price) if price>0 else 0
    final_qty=max(0,min(raw_qty,max_qty,notional_qty))
    return {
        "equity":round(equity,2),
        "reference_price":round(price,4),
        "stop_distance_pct":round(stop_pct,4),
        "volatility_pct":round(volatility,4),
        "base_risk_amount":round(base_risk_amount,2),
        "volatility_multiplier":round(volatility_multiplier,6),
        "adjusted_risk_amount":round(adjusted_risk_amount,2),
        "risk_per_share":round(risk_per_share,4),
        "raw_quantity":raw_qty,
        "maximum_quantity":max_qty,
        "notional_limited_quantity":notional_qty,
        "final_quantity":final_qty,
        "final_notional":round(final_qty*price,2),
    }
