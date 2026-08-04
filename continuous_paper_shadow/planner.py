from __future__ import annotations
from typing import Any
from continuous_paper_shadow.io import digest

def build_plans(
    signals:list[dict[str,Any]],
    account:dict[str,Any],
    policy:dict[str,Any],
)->list[dict[str,Any]]:
    equity=float(account.get("equity",0.0))
    max_notional=float(policy.get("maximum_order_notional",250.0))
    rows=[]
    for signal in signals:
        if signal.get("action")=="HOLD" or float(signal.get("price",0))<=0:
            continue
        price=float(signal["price"])
        notional=min(
            equity*float(policy.get("order_equity_pct",0.1))/100,
            max_notional,
        )
        if price>max_notional:
            continue
        qty=max(1,int(notional//price))
        side="buy" if signal["action"]=="BUY" else "sell"
        body={
            "symbol":signal["symbol"],"side":side,"qty":str(qty),
            "type":"market","time_in_force":"day",
            "strategy_id":signal["strategy_id"],
            "estimated_notional":round(qty*float(signal["price"]),2),
        }
        body["client_order_id"]=digest(body)[:32]
        rows.append(body)
    return rows
