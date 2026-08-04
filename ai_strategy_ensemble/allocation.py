from __future__ import annotations
from typing import Any

def allocate(ranked:list[dict[str,Any]],policy:dict[str,Any])->list[dict[str,Any]]:
    active=[row for row in ranked if row["eligible"]][:int(policy["maximum_active_strategies"])]
    if not active:return []
    total=sum(max(row["score"],0.0001) for row in active)
    maximum=float(policy["maximum_strategy_weight_pct"])
    minimum=float(policy["minimum_strategy_weight_pct"])
    weights=[]
    for row in active:
        raw=row["score"]/total*100.0
        weights.append({"strategy_id":row["strategy_id"],"role":row["role"],"score":row["score"],"weight_pct":max(minimum,min(maximum,raw))})
    weight_total=sum(row["weight_pct"] for row in weights) or 1.0
    for row in weights:
        row["weight_pct"]=round(row["weight_pct"]/weight_total*100.0,4)
    return weights
