from __future__ import annotations
from pathlib import Path
from automated_backtest.io import load_json

def build_dashboard_payload(root: Path) -> dict:
    result = load_json(
        root / "release/v98_01_to_v98_32/actual/"
        "automated_backtest_result.json"
    )
    return {
        "automated_backtest_state": result.get("state", "NOT_AVAILABLE"),
        "run_id": result.get("run_id"),
        "strategy_count": result.get("strategy_count", 0),
        "dataset_count": result.get("dataset_count", 0),
        "window_count": result.get("window_count", 0),
        "job_count": result.get("job_count", 0),
        "cache_hit_count": result.get("cache_hit_count", 0),
        "aggregation": result.get("aggregation", {}),
        "failed_checks": result.get("failed_checks", []),
        "paper_only": True,
    }
