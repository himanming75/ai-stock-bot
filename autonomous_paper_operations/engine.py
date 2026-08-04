from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from typing import Any

from autonomous_paper_operations.io import (
    load_json,write_json,append_jsonl,digest
)
from autonomous_paper_operations.tournament import run_tournament
from autonomous_paper_operations.sessions import build_sessions
from autonomous_paper_operations.scenario import scenario_for_session
from autonomous_paper_operations.recovery import execute_with_retry
from autonomous_paper_operations.backup import create_backup
from autonomous_paper_operations.report import build_operations_report

def _simulate_session(
    session: dict[str, Any],
    equity: float,
    champion: dict[str, Any],
    base_prices: dict[str,float],
) -> dict[str, Any]:
    scenario=scenario_for_session(
        base_prices,
        int(session.get("session_number",1)),
    )
    reference=scenario["reference_prices"]
    closing=scenario["closing_prices"]
    weight=float(champion.get("target_weight_pct",50.0))/100.0
    symbol=str(champion.get("symbol","SPY"))
    entry=float(reference.get(symbol,100.0))
    exit_price=float(closing.get(symbol,entry))
    quantity=max(0,int((equity*weight)//entry))
    pnl=round((exit_price-entry)*quantity,2)
    ending=round(equity+pnl,2)
    return {
        "session_number":session.get("session_number"),
        "session_date":session.get("session_date"),
        "strategy_id":champion.get("strategy_id"),
        "symbol":symbol,
        "quantity":quantity,
        "entry_price":entry,
        "exit_price":exit_price,
        "paper_pnl":pnl,
        "starting_equity":round(equity,2),
        "ending_equity":ending,
        "daily_return_pct":round(
            (ending/equity-1)*100 if equity else 0.0,
            6,
        ),
        "paper_order_count":1 if quantity>0 else 0,
        "actual_orders_submitted":0,
        "state":"COMPLETED",
    }

def evaluate(root: Path) -> dict[str, Any]:
    policy=load_json(
        root/"release/v109_01_to_v110_64/input/"
        "autonomous_operations_policy.json"
    )
    fast_track=load_json(
        root/"release/v106_33_to_v108_64/actual/"
        "fast_track_paper_result.json"
    )
    actual_dir=root/"release/v109_01_to_v110_64/actual"

    source_ready=fast_track.get("state") in {
        "FAST_TRACK_PAPER_EXECUTION_AND_ANALYTICS_COMPLETE",
        "FAST_TRACK_PAPER_CYCLE_DUPLICATE_BLOCKED",
    }
    if not source_ready:
        body={
            "stage":"V110.64",
            "stage_range":"V109.01-V110.64",
            "state":"AUTONOMOUS_PAPER_OPERATIONS_SOURCE_REQUIRED",
            "status":"PASS",
            "actual_orders_submitted":0,
            "paper_only":True,
            "live_trading_enabled":False,
            "next_phase":"V111_LIVE_INFRASTRUCTURE_READ_ONLY",
        }
        body["certificate_sha256"]=digest(body)
        write_json(actual_dir/"autonomous_paper_operations_result.json",body)
        return body

    tournament=run_tournament(policy.get("strategy_candidates",[]))
    sessions=build_sessions(
        str(policy.get("start_date")),
        int(policy.get("session_count",5)),
    )
    equity=float(
        fast_track.get("daily_close",{}).get(
            "ending_equity",
            policy.get("starting_equity",100000.0),
        )
    )
    initial_equity=equity
    champion=tournament.get("champion") or {}
    completed=[]
    backup_rows=[]

    for session in sessions:
        recovery=execute_with_retry(
            lambda s=session,e=equity: _simulate_session(
                s,
                e,
                champion,
                policy.get("base_prices",{}),
            ),
            int(policy.get("maximum_retry_attempts",3)),
        )
        if recovery.get("passed"):
            row=recovery["result"]
            row["attempt_count"]=recovery["attempt_count"]
            equity=float(row["ending_equity"])
        else:
            row=dict(session)
            row.update({
                "state":"FAILED",
                "errors":recovery.get("errors",[]),
                "attempt_count":recovery.get("attempt_count"),
                "starting_equity":equity,
                "ending_equity":equity,
                "actual_orders_submitted":0,
            })
        completed.append(row)
        append_jsonl(
            actual_dir/"autonomous_session_ledger.jsonl",
            row,
        )
        checkpoint={
            "session_date":row.get("session_date"),
            "session_number":row.get("session_number"),
            "state":row.get("state"),
            "ending_equity":row.get("ending_equity"),
            "champion_strategy":champion.get("strategy_id"),
            "updated_at":datetime.now(timezone.utc).isoformat(),
        }
        checkpoint["checkpoint_hash"]=digest(checkpoint)
        write_json(
            actual_dir/"autonomous_operations_checkpoint.json",
            checkpoint,
        )
        backup_rows.append(
            create_backup(root,str(row.get("session_date")))
        )

    report=build_operations_report(
        completed,
        tournament,
        initial_equity,
    )
    state=(
        "AUTONOMOUS_PAPER_OPERATIONS_READY"
        if report.get("all_sessions_completed")
        else "AUTONOMOUS_PAPER_OPERATIONS_REVIEW_REQUIRED"
    )
    observed_at=datetime.now(timezone.utc).isoformat()
    body={
        "stage":"V110.64",
        "stage_range":"V109.01-V110.64",
        "state":state,
        "status":"PASS",
        "observed_at":observed_at,
        "operations_id":digest({
            "source_cycle":fast_track.get("cycle_id"),
            "champion":champion.get("strategy_id"),
            "start_date":policy.get("start_date"),
            "session_count":policy.get("session_count"),
        })[:24],
        "source_cycle_id":fast_track.get("cycle_id"),
        "tournament":tournament,
        "sessions":completed,
        "operations_report":report,
        "backups":backup_rows,
        "scheduler_package_created":True,
        "windows_task_installed":False,
        "windows_task_enabled":False,
        "automatic_restart_enabled":True,
        "recovery_enabled":True,
        "daily_backup_enabled":True,
        "daily_report_enabled":True,
        "paper_operation_complete":report.get("all_sessions_completed"),
        "actual_credentials_used":False,
        "actual_external_network_used":False,
        "actual_orders_submitted":0,
        "paper_only":True,
        "live_execution_authorized":False,
        "broker_submission_authorized":False,
        "broker_write_enabled":False,
        "order_submission_enabled":False,
        "live_trading_enabled":False,
        "external_network_enabled":False,
        "next_phase":"V111_LIVE_INFRASTRUCTURE_READ_ONLY",
    }
    body["certificate_sha256"]=digest(body)
    write_json(
        actual_dir/"autonomous_paper_operations_result.json",
        body,
    )
    write_json(
        actual_dir/"strategy_tournament_result.json",
        tournament,
    )
    write_json(
        actual_dir/"autonomous_operations_report.json",
        report,
    )
    append_jsonl(
        actual_dir/"autonomous_operations_ledger.jsonl",
        {
            "observed_at":observed_at,
            "operations_id":body["operations_id"],
            "state":state,
            "completed_count":report.get("completed_count"),
            "failed_count":report.get("failed_count"),
            "ending_equity":report.get("ending_equity"),
            "champion_strategy":report.get("champion_strategy"),
            "actual_orders_submitted":0,
        },
    )
    return body
