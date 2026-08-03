from __future__ import annotations
from collections import defaultdict
from typing import Any

def select_champion(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    grouped=defaultdict(list)
    for row in results:
        if row.get("state")=="COMPLETED":
            grouped[str(row.get("strategy_id"))].append(row)
    candidates=[]
    for strategy_id,rows in grouped.items():
        scores=[float(row.get("regression_score",0.0)) for row in rows]
        returns=[float(row.get("adjusted_return_pct",0.0)) for row in rows]
        drawdowns=[float(row.get("adjusted_drawdown_pct",0.0)) for row in rows]
        candidates.append({
            "strategy_id":strategy_id,
            "scenario_count":len(rows),
            "average_regression_score":round(sum(scores)/len(scores),6),
            "average_return_pct":round(sum(returns)/len(returns),6),
            "worst_drawdown_pct":round(max(drawdowns),6),
            "all_scenarios_passed":all(row.get("regression_gate",{}).get("passed") for row in rows),
        })
    candidates.sort(
        key=lambda row:(
            row["all_scenarios_passed"],
            row["average_regression_score"],
            -row["worst_drawdown_pct"],
        ),
        reverse=True,
    )
    return candidates[0] if candidates else None
