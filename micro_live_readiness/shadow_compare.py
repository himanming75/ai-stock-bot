from __future__ import annotations
from typing import Any

def compare(candidates:list[dict[str,Any]],policy:dict[str,Any])->dict[str,Any]:
    slippage=float(policy.get("shadow_slippage_bps",5.0))/10000.0
    rows=[]
    for c in candidates:
        estimated=float(c.get("estimated_notional",0.0))
        rows.append({
            "candidate_id":c.get("candidate_id"),
            "symbol":c.get("symbol"),
            "paper_estimated_notional":estimated,
            "shadow_live_estimated_notional":round(estimated*(1+slippage),2),
            "estimated_slippage_amount":round(estimated*slippage,2),
            "actual_live_order_submitted":False,
        })
    return {"rows":rows,"comparison_count":len(rows),"actual_live_orders_submitted":0}
