from __future__ import annotations
from typing import Any

def risk_score(
    exposure: dict[str, Any],
    var_result: dict[str, Any],
    drawdown: dict[str, Any],
    stress: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    score=0.0
    score+=min(30.0,float(exposure.get("largest_strategy_weight_pct",0.0))*0.6)
    score+=min(20.0,float(exposure.get("turnover_pct",0.0))*0.5)
    score+=min(20.0,float(var_result.get("var_pct",0.0))*2.0)
    score+=min(20.0,float(drawdown.get("weighted_drawdown_pct",0.0)))
    score+=min(10.0,float(stress.get("worst_estimated_loss_pct",0.0))*0.5)
    score=round(min(100.0,score),6)

    if score < 30:
        level="LOW"
    elif score < 60:
        level="MEDIUM"
    elif score < 80:
        level="HIGH"
    else:
        level="CRITICAL"

    return {
        "risk_score":score,
        "risk_level":level,
        "maximum_allowed_score":float(policy.get("maximum_risk_score",70.0)),
        "passed":score<=float(policy.get("maximum_risk_score",70.0)),
    }
