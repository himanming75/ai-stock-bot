from __future__ import annotations
from typing import Any

def drawdown_risk(
    portfolio_result: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    weighted=float(
        portfolio_result.get("risk",{}).get("weighted_drawdown_pct",0.0)
    )
    limit=float(policy.get("maximum_weighted_drawdown_pct",15.0))
    return {
        "weighted_drawdown_pct":round(weighted,6),
        "limit_pct":limit,
        "passed":weighted<=limit,
    }
