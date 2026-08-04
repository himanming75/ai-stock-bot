from __future__ import annotations
from datetime import date,datetime,timezone
from pathlib import Path
from typing import Any

from multi_day_scheduler.io import (
    load_json,write_json,append_jsonl,read_jsonl,digest
)
from multi_day_scheduler.calendar import (
    trading_days,next_trading_day,is_trading_day
)
from multi_day_scheduler.queue import build_queue,queue_summary
from multi_day_scheduler.dedup import detect_duplicate_sessions
from multi_day_scheduler.checkpoint import save_checkpoint
from multi_day_scheduler.state import resolve_scheduler_state

def evaluate(
    root: Path,
    start_date: str | None = None,
    session_count: int | None = None,
) -> dict[str, Any]:
    policy=load_json(
        root/"release/v103_33_to_v103_64/input/"
        "multi_day_scheduler_policy.json"
    )
    source_cycle=load_json(
        root/"release/v103_01_to_v103_32/actual/"
        "autonomous_cycle_result.json"
    )
    actual_dir=root/"release/v103_33_to_v103_64/actual"
    queue_path=actual_dir/"multi_day_session_queue.json"
    ledger_path=actual_dir/"multi_day_session_ledger.jsonl"
    checkpoint_path=actual_dir/"multi_day_scheduler_checkpoint.json"

    if start_date is None:
        start_date=date.today().isoformat()
    start=date.fromisoformat(start_date)

    if session_count is None:
        session_count=int(policy.get("default_session_count",5))

    days=[
        day.isoformat()
        for day in trading_days(start,session_count,policy)
    ]
    source_cycle_id=str(source_cycle.get("cycle_id",""))
    previous_queue=load_json(queue_path)

    queue=build_queue(days,source_cycle_id,previous_queue)
    summary=queue_summary(queue)
    duplicate=detect_duplicate_sessions(
        queue.get("sessions",[]),
        read_jsonl(ledger_path),
    )
    resolved=resolve_scheduler_state(source_cycle,summary,duplicate)

    scheduler_id=digest({
        "source_cycle_id":source_cycle_id,
        "start_date":start_date,
        "days":days,
        "policy_version":policy.get("policy_version"),
    })[:24]
    checkpoint=save_checkpoint(
        checkpoint_path,
        scheduler_id,
        queue,
    )
    write_json(queue_path,queue)

    observed_at=datetime.now(timezone.utc).isoformat()
    body={
        "stage":"V103.64",
        "stage_range":"V103.33-V103.64",
        "state":resolved["state"],
        "status":"PASS",
        "observed_at":observed_at,
        "scheduler_id":scheduler_id,
        "source_cycle_id":source_cycle_id,
        "source_cycle_state":source_cycle.get("state"),
        "scheduler_action":resolved["action"],
        "requested_start_date":start_date,
        "requested_session_count":session_count,
        "start_date_is_trading_day":is_trading_day(start,policy),
        "next_trading_day":next_trading_day(start,policy).isoformat(),
        "scheduled_trading_days":days,
        "queue":queue,
        "queue_summary":summary,
        "duplicate_analysis":duplicate,
        "checkpoint":checkpoint,
        "resume_supported":True,
        "approval_granted":False,
        "execution_authorized":False,
        "manual_approval_required":True,
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
        "next_phase":"V104_01_CONTINUOUS_AUTONOMOUS_ENGINE",
    }
    body["multi_day_scheduler_certificate_sha256"]=digest(body)

    write_json(
        actual_dir/"multi_day_scheduler_result.json",
        body,
    )
    append_jsonl(
        actual_dir/"multi_day_scheduler_ledger.jsonl",
        {
            "observed_at":observed_at,
            "scheduler_id":scheduler_id,
            "source_cycle_id":source_cycle_id,
            "state":resolved["state"],
            "scheduled_trading_days":days,
            "session_count":summary["session_count"],
            "duplicate_count":duplicate["duplicate_count"],
            "checkpoint_generation":checkpoint["generation"],
            "actual_orders_submitted":0,
        },
    )
    return body
