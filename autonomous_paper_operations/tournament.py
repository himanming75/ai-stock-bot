from __future__ import annotations
from typing import Any

def score_strategy(row: dict[str, Any]) -> float:
    ret=float(row.get("return_pct",0.0))
    drawdown=abs(float(row.get("max_drawdown_pct",0.0)))
    win_rate=float(row.get("win_rate_pct",0.0))
    sharpe=float(row.get("sharpe",0.0))
    return round(ret*1.0-drawdown*0.7+win_rate*0.05+sharpe*2.0,6)

def run_tournament(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    rankings=[]
    for row in candidates:
        item=dict(row)
        item["tournament_score"]=score_strategy(item)
        rankings.append(item)
    rankings.sort(
        key=lambda x:(x["tournament_score"],x.get("strategy_id","")),
        reverse=True,
    )
    for index,row in enumerate(rankings,start=1):
        row["rank"]=index
    champion=rankings[0] if rankings else None
    return {
        "candidate_count":len(rankings),
        "rankings":rankings,
        "champion":champion,
        "passed":champion is not None,
    }
