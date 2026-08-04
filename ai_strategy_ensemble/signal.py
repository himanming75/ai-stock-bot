from __future__ import annotations
from collections import defaultdict
from typing import Any

def combine(signals:list[dict[str,Any]],allocations:list[dict[str,Any]])->dict[str,Any]:
    weight_map={row["strategy_id"]:float(row["weight_pct"])/100.0 for row in allocations}
    votes=defaultdict(float)
    rows=[]
    for signal in signals:
        sid=str(signal.get("strategy_id",""))
        weight=weight_map.get(sid,0.0)
        action=str(signal.get("action","HOLD")).upper()
        confidence=float(signal.get("confidence",0) or 0)
        contribution=weight*confidence
        signed=contribution if action=="BUY" else (-contribution if action=="SELL" else 0.0)
        votes[str(signal.get("symbol","UNKNOWN"))]+=signed
        rows.append({"strategy_id":sid,"symbol":signal.get("symbol"),"action":action,"weight":weight,"confidence":confidence,"signed_contribution":round(signed,6)})
    outputs=[]
    for symbol,value in sorted(votes.items()):
        action="BUY" if value>0.05 else ("SELL" if value<-0.05 else "HOLD")
        outputs.append({"symbol":symbol,"action":action,"ensemble_score":round(value,6)})
    return {"contributions":rows,"signals":outputs}
