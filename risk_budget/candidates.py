from __future__ import annotations
from typing import Any

def build_candidates(
    portfolio_result: dict[str, Any],
    metrics: dict[str, Any],
) -> list[dict[str, Any]]:
    metric_rows={
        str(row.get("strategy_id")):row
        for row in metrics.get("strategies",[])
        if row.get("strategy_id")
    }
    output=[]
    for allocation in portfolio_result.get("allocation",{}).get("allocations",[]):
        strategy_id=str(allocation.get("strategy_id",""))
        metric=metric_rows.get(strategy_id,{})
        output.append({
            "strategy_id":strategy_id,
            "target_weight_pct":float(allocation.get("target_weight_pct",0.0)),
            "observed_volatility_pct":float(metric.get("observed_volatility_pct",2.0)),
            "win_rate_pct":float(metric.get("win_rate_pct",50.0)),
            "average_win_pct":float(metric.get("average_win_pct",1.0)),
            "average_loss_pct":float(metric.get("average_loss_pct",-1.0)),
            "risk_quality_score":float(metric.get("risk_quality_score",50.0)),
        })
    return output
