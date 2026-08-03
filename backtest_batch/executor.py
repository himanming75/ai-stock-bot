from __future__ import annotations
from typing import Any

def execute_job(job: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    adjusted_return=job["base_return_pct"]+job["return_shock_pct"]
    adjusted_drawdown=max(0.0,job["base_drawdown_pct"]+job["drawdown_shock_pct"])
    adjusted_win_rate=max(
        0.0,
        min(100.0,job["base_win_rate_pct"]+float(policy.get("win_rate_adjustment_pct",0.0))),
    )
    score=adjusted_return-1.5*adjusted_drawdown+0.02*adjusted_win_rate
    return {
        **job,
        "state":"COMPLETED",
        "status":"PASS",
        "adjusted_return_pct":round(adjusted_return,6),
        "adjusted_drawdown_pct":round(adjusted_drawdown,6),
        "adjusted_win_rate_pct":round(adjusted_win_rate,6),
        "regression_score":round(score,6),
    }
