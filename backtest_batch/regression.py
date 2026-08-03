from __future__ import annotations
from typing import Any

def evaluate_regression(
    result: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    minimum_return=float(policy.get("minimum_adjusted_return_pct",-100.0))
    maximum_drawdown=float(policy.get("maximum_adjusted_drawdown_pct",100.0))
    minimum_score=float(policy.get("minimum_regression_score",-999999.0))
    checks={
        "minimum_return":float(result.get("adjusted_return_pct",-999999))>=minimum_return,
        "maximum_drawdown":float(result.get("adjusted_drawdown_pct",999999))<=maximum_drawdown,
        "minimum_score":float(result.get("regression_score",-999999))>=minimum_score,
    }
    failed=[name for name,passed in checks.items() if not passed]
    return {"passed":not failed,"checks":checks,"failed":failed}
