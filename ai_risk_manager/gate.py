from __future__ import annotations
from typing import Any

def evaluate_gate(
    exposure: dict[str, Any],
    var_result: dict[str, Any],
    drawdown: dict[str, Any],
    stress: dict[str, Any],
    score: dict[str, Any],
    rebalance_result: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    checks={
        "maximum_single_strategy_weight":(
            float(exposure.get("largest_strategy_weight_pct",0.0))
            <= float(policy.get("maximum_single_strategy_weight_pct",45.0))
        ),
        "minimum_cash":(
            float(exposure.get("cash_weight_pct",0.0))
            >= float(policy.get("minimum_cash_pct",10.0))
        ),
        "maximum_turnover":(
            float(exposure.get("turnover_pct",0.0))
            <= float(policy.get("maximum_turnover_pct",25.0))
        ),
        "maximum_var":(
            float(var_result.get("var_pct",0.0))
            <= float(policy.get("maximum_var_pct",5.0))
        ),
        "maximum_drawdown":drawdown.get("passed") is True,
        "maximum_stress_loss":(
            float(stress.get("worst_estimated_loss_pct",0.0))
            <= float(policy.get("maximum_stress_loss_pct",20.0))
        ),
        "risk_score":score.get("passed") is True,
        "rebalance_risk_passed":(
            rebalance_result.get("risk",{}).get("passed") is True
        ),
        "execution_not_authorized":(
            rebalance_result.get("execution_authorized") is False
        ),
        "manual_approval_required":(
            rebalance_result.get("manual_approval_required") is True
        ),
    }
    failed=[name for name,passed in checks.items() if not passed]
    return {"passed":not failed,"checks":checks,"failed":failed}
