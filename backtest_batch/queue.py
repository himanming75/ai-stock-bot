from __future__ import annotations
from typing import Any
from backtest_batch.io import digest

def build_batch_jobs(
    base_results: list[dict[str, Any]],
    scenarios: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    jobs=[]
    completed=[row for row in base_results if row.get("state")=="COMPLETED"]
    for row in completed:
        for scenario in scenarios:
            payload={
                "base_job_id":row.get("job_id"),
                "scenario_id":scenario.get("scenario_id"),
                "return_shock_pct":scenario.get("return_shock_pct",0.0),
                "drawdown_shock_pct":scenario.get("drawdown_shock_pct",0.0),
            }
            jobs.append({
                "batch_job_id":digest(payload)[:24],
                "base_job_id":row.get("job_id"),
                "strategy_id":row.get("strategy_id"),
                "symbol":row.get("symbol"),
                "window_id":row.get("window_id"),
                "base_return_pct":float(row.get("total_return_pct",0.0)),
                "base_drawdown_pct":float(row.get("maximum_drawdown_pct",0.0)),
                "base_win_rate_pct":float(row.get("win_rate_pct",0.0)),
                "scenario_id":str(scenario.get("scenario_id")),
                "return_shock_pct":float(scenario.get("return_shock_pct",0.0)),
                "drawdown_shock_pct":float(scenario.get("drawdown_shock_pct",0.0)),
            })
    return jobs

def pending_jobs(
    jobs: list[dict[str, Any]],
    checkpoint: dict[str, Any],
) -> list[dict[str, Any]]:
    completed=set(checkpoint.get("completed_job_ids",[]))
    return [job for job in jobs if job["batch_job_id"] not in completed]
