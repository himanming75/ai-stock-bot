from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from automated_backtest.io import load_json, write_json, append_jsonl, digest
from automated_backtest.discovery import discover_datasets, discover_strategies
from automated_backtest.matrix import build_matrix
from automated_backtest.runner import run_job
from automated_backtest.cache import read_cached, write_cached
from automated_backtest.aggregation import aggregate

def evaluate(root: Path, force: bool = False) -> dict[str, Any]:
    policy = load_json(
        root / "release/v98_01_to_v98_32/input/"
        "automated_backtest_policy.json"
    )
    source = load_json(
        root / "release/v97_33_to_v97_64/actual/"
        "paper_broker_snapshot_reconciliation_result.json"
    )

    if source.get("state") != "PAPER_BROKER_SNAPSHOT_RECONCILIATION_PASS":
        return {
            "stage": "V98.32",
            "stage_range": "V98.01-V98.32",
            "state": "AUTOMATED_BACKTEST_SOURCE_REQUIRED",
            "status": "PASS",
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        }

    strategies = discover_strategies(policy)
    datasets = discover_datasets(root, policy)
    windows = list(policy.get("windows", []))
    jobs = build_matrix(strategies, datasets, windows)
    results = []
    cached_count = 0

    for job in jobs:
        cached = {} if force else read_cached(root, job["job_id"])
        if cached:
            result = dict(cached)
            result["cache_hit"] = True
            cached_count += 1
        else:
            try:
                result = run_job(job, policy)
            except Exception as exc:
                result = {
                    **job,
                    "state": "JOB_FAILED",
                    "status": "FAIL",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            result["cache_hit"] = False
            write_cached(root, job["job_id"], result)
        results.append(result)

    aggregation = aggregate(results)
    checks = {
        "strategies_available": bool(strategies),
        "datasets_configured": bool(datasets),
        "windows_available": bool(windows),
        "jobs_created": bool(jobs),
        "no_job_failures": aggregation["failed_count"] == 0,
        "at_least_one_completed": aggregation["completed_count"] > 0,
        "broker_source_reconciled": True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    state = (
        "AUTOMATED_BACKTEST_FRAMEWORK_READY"
        if not failed
        else "AUTOMATED_BACKTEST_FRAMEWORK_REVIEW_REQUIRED"
    )

    body = {
        "stage": "V98.32",
        "stage_range": "V98.01-V98.32",
        "state": state,
        "status": "PASS",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "run_id": digest({
            "strategies": strategies,
            "datasets": datasets,
            "windows": windows,
            "policy_version": policy.get("policy_version"),
        })[:24],
        "strategy_count": len(strategies),
        "dataset_count": len(datasets),
        "window_count": len(windows),
        "job_count": len(jobs),
        "cache_hit_count": cached_count,
        "results": results,
        "aggregation": aggregation,
        "checks": checks,
        "failed_checks": failed,
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "actual_orders_submitted": 0,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "continuous_loop_enabled": False,
        "windows_task_enabled": False,
        "next_phase": "V98_33_BACKTEST_BATCH_ORCHESTRATION",
    }
    body["automated_backtest_certificate_sha256"] = digest(body)

    write_json(
        root / "release/v98_01_to_v98_32/actual/"
        "automated_backtest_result.json",
        body,
    )
    append_jsonl(
        root / "release/v98_01_to_v98_32/actual/"
        "automated_backtest_run_ledger.jsonl",
        {
            "observed_at": body["observed_at"],
            "run_id": body["run_id"],
            "state": state,
            "job_count": body["job_count"],
            "completed_count": aggregation["completed_count"],
            "failed_count": aggregation["failed_count"],
            "cache_hit_count": cached_count,
        },
    )
    return body
