from __future__ import annotations
from itertools import product
from typing import Any
from automated_backtest.io import digest

def build_matrix(
    strategies: list[dict[str, Any]],
    datasets: list[dict[str, Any]],
    windows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    jobs = []
    for strategy, dataset, window in product(strategies, datasets, windows):
        payload = {
            "strategy": strategy,
            "dataset": dataset,
            "window": window,
        }
        jobs.append({
            "job_id": digest(payload)[:24],
            "strategy_id": strategy["strategy_id"],
            "family": strategy["family"],
            "parameters": strategy["parameters"],
            "dataset_id": dataset["dataset_id"],
            "symbol": dataset["symbol"],
            "dataset_path": dataset["path"],
            "dataset_exists": dataset["exists"],
            "window_id": str(window.get("window_id")),
            "start_index": int(window.get("start_index", 0)),
            "end_index": int(window.get("end_index", 0)),
        })
    return jobs
