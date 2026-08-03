from __future__ import annotations
from collections import defaultdict
from typing import Any

def build_candidates(
    batch_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped=defaultdict(list)
    for row in batch_results:
        if row.get("state")!="COMPLETED":
            continue
        grouped[str(row.get("strategy_id"))].append(row)

    candidates=[]
    for strategy_id,rows in grouped.items():
        scores=[float(r.get("regression_score",0.0)) for r in rows]
        returns=[float(r.get("adjusted_return_pct",0.0)) for r in rows]
        drawdowns=[float(r.get("adjusted_drawdown_pct",0.0)) for r in rows]
        passed=[bool(r.get("regression_gate",{}).get("passed")) for r in rows]
        candidates.append({
            "strategy_id":strategy_id,
            "scenario_count":len(rows),
            "average_regression_score":round(sum(scores)/len(scores),6),
            "average_return_pct":round(sum(returns)/len(returns),6),
            "worst_drawdown_pct":round(max(drawdowns),6),
            "pass_rate_pct":round(sum(1 for x in passed if x)/len(passed)*100.0,6),
            "all_scenarios_passed":all(passed),
        })
    return candidates
