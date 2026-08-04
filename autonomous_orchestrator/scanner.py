from __future__ import annotations
from typing import Any

def scan(fixture:dict[str,Any],policy:dict[str,Any])->list[dict[str,Any]]:
    rows=[]
    snapshots=fixture.get("snapshots",{})
    references=policy.get("reference_prices",{})
    threshold=float(policy.get("signal_threshold_pct",0.25))
    for symbol in policy.get("symbols",[]):
        snap=snapshots.get(symbol,{})
        trade=snap.get("latestTrade",{})
        price=float(trade.get("p",0.0) or 0.0)
        reference=float(references.get(symbol,price or 1.0))
        change=(price/reference-1.0)*100.0 if reference else 0.0
        action="BUY" if change>=threshold else "SELL" if change<=-threshold else "HOLD"
        rows.append({
            "symbol":symbol,"price":round(price,4),
            "reference_price":round(reference,4),
            "change_pct":round(change,6),"action":action,
            "strategy_id":"AUTONOMOUS_SNAPSHOT_MOMENTUM",
        })
    return rows
