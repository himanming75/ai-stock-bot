from __future__ import annotations
from pathlib import Path
from backtest_batch.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result=load_json(
        root/"release/v98_33_to_v98_64/actual/backtest_batch_result.json"
    )
    return {
        "batch_state":result.get("state","NOT_AVAILABLE"),
        "batch_id":result.get("batch_id"),
        "job_count":result.get("job_count",0),
        "completed_count":result.get("completed_count",0),
        "failed_count":result.get("failed_count",0),
        "regression_pass_count":result.get("regression_pass_count",0),
        "regression_fail_count":result.get("regression_fail_count",0),
        "champion":result.get("champion"),
        "paper_only":True,
    }
