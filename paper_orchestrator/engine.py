from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from paper_orchestrator.io import (
    append_jsonl,
    digest_payload,
    write_json,
)
from paper_orchestrator.lock import RunLock
from paper_orchestrator.state import (
    STEP_ORDER,
    load_or_new,
    persist,
)
from paper_orchestrator.steps import STEP_FUNCTIONS


def build_run_id(observed_at: str) -> str:
    safe = observed_at.replace(":", "").replace("-", "").replace("+", "_")
    return f"paper-cycle-{safe}"


def run_orchestrator(
    root: Path,
    *,
    observed_at_override: str = "",
    resume: bool = True,
    fail_after_step: str = "",
) -> dict[str, Any]:
    observed_at = (
        observed_at_override
        or datetime.now(timezone.utc).isoformat()
    )
    run_id = build_run_id(observed_at)

    release = root / "release/v88_09_to_v88_16"
    actual = release / "actual"
    lock_path = actual / "paper_orchestrator.lock"
    state_path = actual / "paper_orchestrator_checkpoint.json"
    ledger_path = actual / "paper_orchestrator_ledger.jsonl"
    result_path = actual / "paper_orchestrator_result.json"
    dashboard_path = actual / "paper_orchestrator_dashboard_state.json"
    daily_report_path = actual / "paper_orchestrator_daily_report.json"

    state = load_or_new(state_path, run_id, observed_at)
    if not resume and state_path.exists():
        state_path.unlink()
        state = load_or_new(state_path, run_id, observed_at)

    with RunLock(lock_path, run_id):
        try:
            for step_name in STEP_ORDER:
                if step_name in state["completed_steps"]:
                    continue

                state["current_step"] = step_name
                persist(state_path, state)

                step_result = STEP_FUNCTIONS[step_name](root)
                append_jsonl(ledger_path, {
                    "run_id": run_id,
                    "observed_at": observed_at,
                    "step": step_name,
                    "status": "PASS",
                    "result": step_result,
                })
                state["completed_steps"].append(step_name)
                persist(state_path, state)

                if fail_after_step and step_name == fail_after_step:
                    raise RuntimeError(
                        f"simulated failure after {step_name}"
                    )

            state["state"] = "PAPER_AUTOMATION_ORCHESTRATOR_READY"
            state["current_step"] = ""
            state["safe_mode"] = False
            state["failed_step"] = ""
            state["error"] = ""
            persist(state_path, state)

        except Exception as exc:
            state["state"] = "PAPER_ORCHESTRATOR_SAFE_MODE"
            state["safe_mode"] = True
            state["failed_step"] = state.get("current_step", "")
            state["error"] = str(exc)
            persist(state_path, state)
            append_jsonl(ledger_path, {
                "run_id": run_id,
                "observed_at": observed_at,
                "step": state.get("current_step", ""),
                "status": "FAIL",
                "error": str(exc),
            })

    complete = len(state["completed_steps"]) == len(STEP_ORDER)
    status = "PASS" if complete and not state["safe_mode"] else "BLOCKED"

    report = {
        "run_id": run_id,
        "observed_at": observed_at,
        "completed_step_count": len(state["completed_steps"]),
        "total_step_count": len(STEP_ORDER),
        "completed_steps": state["completed_steps"],
        "safe_mode": state["safe_mode"],
        "failed_step": state["failed_step"],
        "state": state["state"],
        "paper_only": True,
    }
    report["report_sha256"] = digest_payload(report)

    result = {
        "stage": "V88.16",
        "stage_range": "V88.09-V88.16",
        "state": state["state"],
        "status": status,
        "implementation_type": "LOCAL_PAPER_AUTOMATION_ORCHESTRATOR",
        "run_id": run_id,
        "observed_at": observed_at,
        "completed_steps": state["completed_steps"],
        "completed_step_count": len(state["completed_steps"]),
        "total_step_count": len(STEP_ORDER),
        "safe_mode": state["safe_mode"],
        "failed_step": state["failed_step"],
        "error": state["error"],
        "checkpoint_path": str(state_path.resolve()),
        "ledger_path": str(ledger_path.resolve()),
        "daily_report_path": str(daily_report_path.resolve()),
        "paper_only": True,
        "continuous_loop_enabled": False,
        "windows_task_enabled": False,
        "automatic_broker_execution_enabled": False,
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "broker_command_execution_enabled": False,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "actual_paper_orders_submitted": 0,
        "live_orders_submitted": 0,
        "next_phase": (
            "V88_17_PAPER_PRODUCTION_RELEASE"
            if status == "PASS"
            else "V88_09_TO_V88_16_RESUME"
        ),
    }

    write_json(daily_report_path, report)
    write_json(result_path, result)
    write_json(dashboard_path, {
        "paper_orchestrator_state": result["state"],
        "status": result["status"],
        "completed_step_count": result["completed_step_count"],
        "total_step_count": result["total_step_count"],
        "safe_mode": result["safe_mode"],
        "failed_step": result["failed_step"],
        "observed_at": observed_at,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
    })
    return result
