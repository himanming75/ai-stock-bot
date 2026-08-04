from __future__ import annotations
from typing import Any
from autonomous_orchestrator.io import digest

def build(candidates:list[dict[str,Any]],risk:dict[str,Any])->list[dict[str,Any]]:
    qty=int(risk.get("dynamic_sizing",{}).get("final_quantity",0) or 0)
    rows=[]
    for c in candidates:
        if qty<=0: continue
        plan={
            "symbol":c.get("symbol"),
            "side":"buy" if c.get("action")=="BUY" else "sell",
            "qty":str(qty),
            "type":"market",
            "time_in_force":"day",
            "strategy_id":c.get("strategy_id"),
            "estimated_price":c.get("price"),
            "estimated_notional":round(float(c.get("price",0))*qty,2),
        }
        plan["client_order_id"]=digest(plan)[:32]
        rows.append(plan)
    return rows
