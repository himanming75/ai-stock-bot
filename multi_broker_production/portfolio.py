from __future__ import annotations
from collections import defaultdict
from typing import Any

def aggregate(snapshots:list[dict[str,Any]])->dict[str,Any]:
    total_equity=sum(float(x["equity"]) for x in snapshots)
    total_cash=sum(float(x["cash"]) for x in snapshots)
    total_buying_power=sum(float(x["buying_power"]) for x in snapshots)
    positions=[]
    broker_values=defaultdict(float)
    for s in snapshots:
        broker_values[s["broker_id"]]+=float(s["equity"])
        for p in s.get("positions",[]):
            positions.append({"broker_id":s["broker_id"],"account_id_masked":s["account_id_masked"],**p})
    gross_exposure=sum(abs(float(p.get("market_value",0) or 0)) for p in positions)
    allocation=[]
    for name,value in sorted(broker_values.items()):
        allocation.append({
            "broker_id":name,
            "equity":round(value,2),
            "weight_pct":round(value/(total_equity or 1)*100,4),
        })
    return {
        "summary":{
            "broker_count":len(snapshots),
            "account_count":len(snapshots),
            "position_count":len(positions),
            "total_equity":round(total_equity,2),
            "total_cash":round(total_cash,2),
            "total_buying_power":round(total_buying_power,2),
            "gross_exposure":round(gross_exposure,2),
            "gross_exposure_pct":round(gross_exposure/(total_equity or 1)*100,4),
            "cash_weight_pct":round(total_cash/(total_equity or 1)*100,4),
        },
        "positions":positions,
        "broker_allocation":allocation,
    }
