from __future__ import annotations
from typing import Any

def _f(v:Any)->float:
    try:return float(v)
    except Exception:return 0.0

def drawdown(peak_equity:Any,current_equity:Any)->float:
    peak=_f(peak_equity);current=_f(current_equity)
    return round((peak-current)/peak*100,4) if peak>0 else 0.0

def daily_loss(start_equity:Any,current_equity:Any)->float:
    start=_f(start_equity);current=_f(current_equity)
    return round(max(0.0,(start-current)/start*100),4) if start>0 else 0.0

def position_size(equity:Any,risk_pct:Any,entry_price:Any,stop_price:Any,max_qty:int,max_notional:float)->dict[str,Any]:
    eq=_f(equity);risk=_f(risk_pct)/100;entry=_f(entry_price);stop=_f(stop_price)
    risk_per_share=abs(entry-stop)
    budget=eq*risk
    qty=int(budget/risk_per_share) if risk_per_share>0 else 0
    qty=min(qty,int(max_qty))
    if entry>0:qty=min(qty,int(max_notional/entry))
    return {"risk_budget":round(budget,2),"risk_per_share":round(risk_per_share,4),"quantity":max(0,qty),"estimated_notional":round(max(0,qty)*entry,2)}
