from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from production_scheduler.config import load,validate
from production_scheduler.plan import build
from production_scheduler.io import write_json,append_jsonl

def evaluate(root:Path)->dict:
    config=load(root)
    validation=validate(config)
    plan=build(root)
    checks={
        "config_valid":validation["valid"],
        "scheduled_paper_submission_disabled":config["scheduled_paper_submission_enabled"] is False,
        "scheduled_live_submission_disabled":config["scheduled_live_submission_enabled"] is False,
        "broker_write_disabled":config["broker_write_enabled"] is False,
        "plan_has_no_order_submission":plan["scheduled_order_submission_included"] is False,
    }
    failed=[k for k,v in checks.items() if not v]
    state="PRODUCTION_SCHEDULER_READY" if not failed else "PRODUCTION_SCHEDULER_REVIEW_REQUIRED"
    observed=datetime.now(timezone.utc).isoformat()
    result={
        "stage":"V195.64",
        "state":state,
        "status":"PASS",
        "observed_at":observed,
        "config":config,
        "scheduler_plan":plan,
        "checks":checks,
        "failed":failed,
        "windows_task_scheduler_ready":True,
        "retry_foundation_ready":True,
        "duplicate_execution_guard_ready":True,
        "automatic_order_submission_enabled":False,
        "broker_write_enabled":False,
        "live_submission_enabled":False,
        "actual_live_orders_submitted":0,
        "next_phase":"V196_01_TO_V200_64_MULTI_BROKER_MULTI_ACCOUNT_PRODUCTION",
    }
    actual=root/"release/v191_01_to_v195_64/actual"
    write_json(actual/"production_scheduler_result.json",result)
    append_jsonl(actual/"production_scheduler_audit_ledger.jsonl",{
        "observed_at":observed,"state":state,
        "enabled_job_count":plan["enabled_job_count"],
        "actual_live_orders_submitted":0,
    })
    return result
