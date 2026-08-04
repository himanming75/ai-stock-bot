from __future__ import annotations
from collections import defaultdict
from typing import Any
from paper_qualification.metrics import compute

def score(metrics:dict[str,Any])->float:
    value=0.0
    value+=min(30.0,max(0.0,metrics.get("win_rate_pct",0)*0.4))
    value+=min(30.0,max(0.0,metrics.get("profit_factor",0)*15.0))
    value+=min(25.0,max(0.0,(metrics.get("sharpe",0)+1)*8.0))
    value+=max(0.0,15.0-metrics.get("maximum_drawdown_pct",0))
    return round(min(100.0,value),2)

def analyze(trades:list[dict[str,Any]],daily:list[dict[str,Any]])->list[dict[str,Any]]:
    groups=defaultdict(list)
    for trade in trades:
        groups[str(trade.get("strategy_id","UNKNOWN"))].append(trade)
    rows=[]
    for name,items in groups.items():
        m=compute(items,daily)
        rows.append({"strategy_id":name,"metrics":m,"score":score(m),"grade":grade(score(m))})
    rows.sort(key=lambda x:x["score"],reverse=True)
    return rows

def grade(value:float)->str:
    if value>=90:return "A"
    if value>=80:return "B"
    if value>=70:return "C"
    if value>=60:return "D"
    return "F"
