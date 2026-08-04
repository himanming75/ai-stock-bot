from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from daily_paper_runner.io import (
    load_json, write_json, append_jsonl, read_jsonl, digest
)
from daily_paper_runner.session import select_session
from daily_paper_runner.preflight import evaluate_preflight
from daily_paper_runner.approval import build_paper_approval
from daily_paper_runner.plan import build_daily_plan
from daily_paper_runner.dedup import detect_duplicate
from daily_paper_runner.checkpoint import save_checkpoint
from daily_paper_runner.report import build_report

def evaluate(
    root: Path,
    session_date: str | None = None,
) -> dict[str, Any]:
    policy = load_json(
        root / "release/v106_01_to_v106_32/input/"
        "daily_paper_runner_policy.json"
    )
    final_release = load_json(
        root / "release/v105_33_to_v105_64/actual/"
        "production_readiness_final_release_result.json"
    )
    scheduler = load_json(
        root / "release/v103_33_to_v103_64/actual/"
        "multi_day_scheduler_result.json"
    )
    continuous_runtime = load_json(
        root / "release/v104_33_to_v104_64/actual/"
        "continuous_service_runtime_result.json"
    )
    decision = load_json(
        root / "release/v102_33_to_v102_64/actual/"
        "autonomous_decision_result.json"
    )
    portfolio = load_json(
        root / "release/v99_01_to_v99_32/actual/"
        "ai_portfolio_manager_result.json"
    )

    actual_dir = root / "release/v106_01_to_v106_32/actual"
    ledger_path = actual_dir / "daily_paper_trading_ledger.jsonl"
    checkpoint_path = actual_dir / "daily_paper_runner_checkpoint.json"

    selected = select_session(scheduler, session_date)
    session = selected.get("session") or {}
    run_key = digest({
        "session_id": session.get("session_id"),
        "session_date": session.get("session_date"),
        "release_id": final_release.get("release_id"),
        "policy_version": policy.get("policy_version"),
    })
    run_id = digest({"run_key": run_key, "kind": "V106"})[:24]
    duplicate = detect_duplicate(run_key, read_jsonl(ledger_path))

    if duplicate.get("duplicate"):
        body = {
            "stage": "V106.32",
            "stage_range": "V106.01-V106.32",
            "state": "DAILY_PAPER_TRADING_DUPLICATE_RUN_BLOCKED",
            "status": "PASS",
            "run_id": run_id,
            "run_key": run_key,
            "selected_session": selected,
            "duplicate": duplicate,
            "paper_simulation_authorized": False,
            "live_execution_authorized": False,
            "actual_orders_submitted": 0,
            "paper_only": True,
            "next_phase": "V106_33_INTRADAY_PAPER_EXECUTION_ENGINE",
        }
        body["daily_runner_certificate_sha256"] = digest(body)
        write_json(actual_dir / "daily_paper_runner_result.json", body)
        return body

    preflight = evaluate_preflight(
        final_release,
        scheduler,
        continuous_runtime,
        selected,
        policy,
    )
    approval = build_paper_approval(preflight, policy)
    plan = build_daily_plan(session, decision, portfolio, approval)

    if not selected.get("session_available"):
        state = "DAILY_PAPER_TRADING_SOURCE_REQUIRED"
    elif not preflight.get("passed"):
        state = "DAILY_PAPER_TRADING_PREFLIGHT_BLOCKED"
    elif plan.get("plan_count", 0) == 0:
        state = "DAILY_PAPER_TRADING_RUN_NO_ACTION"
    else:
        state = "DAILY_PAPER_TRADING_RUN_COMPLETED"

    checkpoint = save_checkpoint(
        checkpoint_path,
        run_id,
        state,
        session,
        plan,
    )
    report = build_report(
        state,
        session,
        preflight,
        approval,
        plan,
    )
    observed_at = datetime.now(timezone.utc).isoformat()

    body = {
        "stage": "V106.32",
        "stage_range": "V106.01-V106.32",
        "state": state,
        "status": "PASS",
        "observed_at": observed_at,
        "run_id": run_id,
        "run_key": run_key,
        "source_release_id": final_release.get("release_id"),
        "selected_session": selected,
        "preflight": preflight,
        "paper_approval": approval,
        "daily_plan": plan,
        "daily_report": report,
        "duplicate": duplicate,
        "checkpoint": checkpoint,
        "paper_simulation_authorized": approval.get(
            "paper_simulation_authorized"
        ) is True,
        "paper_plans_authorized": report.get("authorized_plan_count", 0),
        "paper_plans_processed": 0,
        "live_execution_authorized": False,
        "broker_submission_authorized": False,
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "actual_orders_submitted": 0,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "background_service_running": False,
        "windows_task_enabled": False,
        "next_phase": "V106_33_INTRADAY_PAPER_EXECUTION_ENGINE",
    }
    body["daily_runner_certificate_sha256"] = digest(body)

    write_json(actual_dir / "daily_paper_runner_result.json", body)
    write_json(actual_dir / "daily_paper_trading_report.json", report)
    append_jsonl(
        ledger_path,
        {
            "observed_at": observed_at,
            "run_id": run_id,
            "run_key": run_key,
            "state": state,
            "session_id": session.get("session_id"),
            "session_date": session.get("session_date"),
            "preflight_passed": preflight.get("passed"),
            "paper_simulation_authorized": approval.get(
                "paper_simulation_authorized"
            ),
            "paper_plans_authorized": report.get("authorized_plan_count", 0),
            "actual_orders_submitted": 0,
        },
    )
    return body
