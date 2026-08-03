from __future__ import annotations
from typing import Any

def score_candidate(candidate: dict[str, Any], policy: dict[str, Any]) -> float:
    return_weight=float(policy.get("return_weight",1.0))
    score_weight=float(policy.get("regression_score_weight",1.0))
    drawdown_penalty=float(policy.get("drawdown_penalty",1.5))
    stability_weight=float(policy.get("stability_weight",0.05))
    bonus=float(policy.get("all_scenarios_passed_bonus",2.0)) if candidate.get("all_scenarios_passed") else 0.0
    value=(
        return_weight*float(candidate.get("average_return_pct",0.0))
        + score_weight*float(candidate.get("average_regression_score",0.0))
        - drawdown_penalty*float(candidate.get("worst_drawdown_pct",0.0))
        + stability_weight*float(candidate.get("pass_rate_pct",0.0))
        + bonus
    )
    return round(value,6)

def rank_candidates(
    candidates: list[dict[str, Any]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    rows=[]
    for candidate in candidates:
        item=dict(candidate)
        item["portfolio_score"]=score_candidate(item,policy)
        rows.append(item)
    rows.sort(key=lambda row:row["portfolio_score"],reverse=True)
    for rank,row in enumerate(rows,1):
        row["rank"]=rank
    return rows
