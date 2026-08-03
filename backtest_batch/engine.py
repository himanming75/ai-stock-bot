from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

from backtest_batch.io import load_json,write_json,append_jsonl,digest
from backtest_batch.queue import build_batch_jobs,pending_jobs
from backtest_batch.executor import execute_job
from backtest_batch.retry import execute_with_retry
from backtest_batch.regression import evaluate_regression
from backtest_batch.champion import select_champion

def evaluate(root: Path, resume: bool=True) -> dict[str, Any]:
    policy=load_json(root/"release/v98_33_to_v98_64/input/batch_policy.json")
    source=load_json(root/"release/v98_01_to_v98_32/actual/automated_backtest_result.json")
    checkpoint_path=root/"release/v98_33_to_v98_64/actual/batch_checkpoint.json"
    checkpoint=load_json(checkpoint_path) if resume else {}

    if source.get("state")!="AUTOMATED_BACKTEST_FRAMEWORK_READY":
        return {
            "stage":"V98.64","stage_range":"V98.33-V98.64",
            "state":"BACKTEST_BATCH_SOURCE_REQUIRED","status":"PASS",
            "paper_only":True,"broker_write_enabled":False,
            "order_submission_enabled":False,"live_trading_enabled":False,
            "external_network_enabled":False,
        }

    jobs=build_batch_jobs(
        source.get("results",[]),
        list(policy.get("scenarios",[])),
    )
    pending=pending_jobs(jobs,checkpoint)
    prior_results=list(checkpoint.get("results",[]))
    completed_ids=set(checkpoint.get("completed_job_ids",[]))
    maximum_retries=int(policy.get("maximum_retries",1))

    for job in pending:
        result=execute_with_retry(
            job,
            lambda item:execute_job(item,policy),
            maximum_retries,
        )
        if result.get("state")=="COMPLETED":
            result["regression_gate"]=evaluate_regression(result,policy)
            completed_ids.add(job["batch_job_id"])
        prior_results.append(result)
        write_json(checkpoint_path,{
            "completed_job_ids":sorted(completed_ids),
            "results":prior_results,
        })

    completed=[row for row in prior_results if row.get("state")=="COMPLETED"]
    failed=[row for row in prior_results if row.get("status")=="FAIL"]
    gate_passed=[row for row in completed if row.get("regression_gate",{}).get("passed")]
    gate_failed=[row for row in completed if not row.get("regression_gate",{}).get("passed")]
    champion=select_champion(completed)

    checks={
        "jobs_created":bool(jobs),
        "all_jobs_terminal":len(completed)+len(failed)==len(jobs),
        "no_execution_failures":not failed,
        "regression_results_present":bool(completed),
        "champion_available":champion is not None,
    }
    failed_checks=[name for name,passed in checks.items() if not passed]
    state=(
        "BACKTEST_BATCH_REGRESSION_READY"
        if not failed_checks
        else "BACKTEST_BATCH_REGRESSION_REVIEW_REQUIRED"
    )
    observed=datetime.now(timezone.utc).isoformat()
    body={
        "stage":"V98.64","stage_range":"V98.33-V98.64",
        "state":state,"status":"PASS","observed_at":observed,
        "batch_id":digest({
            "source_run_id":source.get("run_id"),
            "scenarios":policy.get("scenarios",[]),
            "policy_version":policy.get("policy_version"),
        })[:24],
        "source_run_id":source.get("run_id"),
        "job_count":len(jobs),
        "completed_count":len(completed),
        "failed_count":len(failed),
        "regression_pass_count":len(gate_passed),
        "regression_fail_count":len(gate_failed),
        "resume_enabled":resume,
        "checkpoint_completed_count":len(completed_ids),
        "results":prior_results,
        "champion":champion,
        "checks":checks,
        "failed_checks":failed_checks,
        "actual_credentials_used":False,
        "actual_external_network_used":False,
        "actual_orders_submitted":0,
        "network_requests_executed":0,
        "write_requests_executed":0,
        "paper_only":True,
        "broker_write_enabled":False,
        "order_submission_enabled":False,
        "live_trading_enabled":False,
        "external_network_enabled":False,
        "continuous_loop_enabled":False,
        "windows_task_enabled":False,
        "next_phase":"V99_01_AI_PORTFOLIO_MANAGER",
    }
    body["batch_regression_certificate_sha256"]=digest(body)
    write_json(
        root/"release/v98_33_to_v98_64/actual/backtest_batch_result.json",
        body,
    )
    append_jsonl(
        root/"release/v98_33_to_v98_64/actual/backtest_batch_ledger.jsonl",
        {
            "observed_at":observed,
            "batch_id":body["batch_id"],
            "state":state,
            "job_count":len(jobs),
            "completed_count":len(completed),
            "failed_count":len(failed),
            "regression_pass_count":len(gate_passed),
            "regression_fail_count":len(gate_failed),
            "champion_strategy":champion.get("strategy_id") if champion else None,
        },
    )
    return body
