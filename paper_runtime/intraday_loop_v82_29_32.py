
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


STAGES = (
    "SESSION",
    "SCHEDULER",
    "SIGNAL",
    "RISK",
    "AUTHORIZATION",
    "SHADOW_EXECUTION",
    "PORTFOLIO",
    "ANALYTICS",
    "DASHBOARD",
)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")


def make_loop_id(session_id: str, tick_id: str, observed_at: str) -> str:
    raw = f"{session_id}|{tick_id}|{observed_at}".encode("utf-8")
    return "intraday-loop-" + hashlib.sha256(raw).hexdigest()[:20]


def run_intraday_loop(
    *,
    session_result_path: Path,
    scheduler_result_path: Path,
    signal_path: Path,
    risk_result_path: Path,
    authorization_result_path: Path,
    execution_result_path: Path,
    portfolio_result_path: Path,
    analytics_result_path: Path,
    policy_path: Path,
    loop_lock_path: Path,
    loop_ledger_path: Path,
    recovery_path: Path,
    dashboard_path: Path,
    result_path: Path,
    execute_loop: bool = False,
    resume_loop: bool = False,
    stage_callbacks: dict[str, Callable[[], dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    observed_at = datetime.now(timezone.utc).isoformat()
    issues: list[dict[str, Any]] = []

    inputs = {}
    paths = {
        "session": session_result_path,
        "scheduler": scheduler_result_path,
        "signal": signal_path,
        "risk": risk_result_path,
        "authorization": authorization_result_path,
        "execution": execution_result_path,
        "portfolio": portfolio_result_path,
        "analytics": analytics_result_path,
        "policy": policy_path,
    }

    for name, path in paths.items():
        try:
            inputs[name] = load_json(path)
        except Exception as exc:
            inputs[name] = {}
            issues.append({
                "code": f"INVALID_{name.upper()}_INPUT",
                "blocking": True,
                "detail": str(exc),
            })

    policy = inputs["policy"]
    if not policy:
        issues.append({
            "code": "INTRADAY_LOOP_POLICY_NOT_FOUND",
            "blocking": True,
            "detail": str(policy_path),
        })

    safety_checks = (
        ("PAPER_ONLY_REQUIRED", bool(policy.get("paper_only", False))),
        (
            "BROKER_WRITE_MUST_BE_DISABLED",
            not bool(policy.get("broker_write_enabled", True)),
        ),
        (
            "ORDER_SUBMISSION_MUST_BE_DISABLED",
            not bool(policy.get("order_submission_enabled", True)),
        ),
        (
            "LIVE_TRADING_MUST_BE_DISABLED",
            not bool(policy.get("live_trading_enabled", True)),
        ),
        (
            "CONTINUOUS_LOOP_MUST_BE_DISABLED",
            not bool(policy.get("continuous_loop_enabled", True)),
        ),
    )
    for code, passed in safety_checks:
        if not passed:
            issues.append({
                "code": code,
                "blocking": True,
                "detail": "intraday loop safety policy failed",
            })

    session = inputs["session"]
    scheduler = inputs["scheduler"]
    risk = inputs["risk"]
    authorization = inputs["authorization"]

    session_ready = (
        session.get("state") == "PAPER_SESSION_RUNNING"
        and bool(session.get("session_active", False))
    )
    scheduler_ready = scheduler.get("state") in {
        "PAPER_SCHEDULER_TICK_AUTHORIZED",
        "PAPER_SCHEDULER_TICK_COMPLETED",
    }
    tick_authorized = bool(scheduler.get("tick_authorized", False))
    risk_clear = risk.get("state") == "SHADOW_RISK_CLEAR"
    authorization_ready = authorization.get("state") in {
        "SHADOW_TRADE_AUTHORIZED",
        "SHADOW_TRADE_NO_ACTION",
        "SHADOW_TRADE_REJECTED",
    }

    session_id = str(session.get("session_id", ""))
    tick_id = str(scheduler.get("tick_id", ""))

    existing_lock = load_json(loop_lock_path)
    active_loop = bool(existing_lock.get("active", False))
    duplicate_loop = execute_loop and active_loop and not resume_loop
    if duplicate_loop:
        issues.append({
            "code": "DUPLICATE_INTRADAY_LOOP_BLOCKED",
            "blocking": True,
            "detail": str(existing_lock.get("loop_id", "")),
        })

    recovery_available = (
        active_loop
        and not bool(existing_lock.get("completed", False))
    )

    gate_reasons: list[str] = []
    if not session_ready:
        gate_reasons.append("PAPER_SESSION_NOT_RUNNING")
    if not scheduler_ready or not tick_authorized:
        gate_reasons.append("SCHEDULER_TICK_NOT_AUTHORIZED")
    if not risk_clear:
        gate_reasons.append("RISK_NOT_CLEAR")
    if not authorization_ready:
        gate_reasons.append("TRADE_AUTHORIZATION_NOT_READY")

    blocking = any(item.get("blocking") for item in issues)
    loop_started = False
    loop_completed = False
    loop_recovered = False
    ledger_written = False
    recovery_written = False
    current_loop_id = str(existing_lock.get("loop_id", ""))
    stage_results: list[dict[str, Any]] = []
    last_completed_stage = ""

    if blocking:
        state, status = "INTRADAY_LOOP_SAFE_MODE", "BLOCKED"
    elif not execute_loop and not resume_loop:
        if gate_reasons:
            state, status = "INTRADAY_LOOP_WAIT_GATES", "PASS"
        else:
            state, status = "INTRADAY_LOOP_READY", "PASS"
    elif gate_reasons:
        state, status = "INTRADAY_LOOP_WAIT_GATES", "PASS"
    elif resume_loop and not recovery_available:
        state, status = "INTRADAY_LOOP_RECOVERY_NOT_AVAILABLE", "PASS"
    else:
        if resume_loop:
            current_loop_id = str(existing_lock.get("loop_id", ""))
            last_completed_stage = str(
                existing_lock.get("last_completed_stage", "")
            )
            loop_recovered = True
        else:
            current_loop_id = make_loop_id(
                session_id,
                tick_id,
                observed_at,
            )

        write_json(loop_lock_path, {
            "stage": "V82.29",
            "active": True,
            "completed": False,
            "loop_id": current_loop_id,
            "session_id": session_id,
            "tick_id": tick_id,
            "last_completed_stage": last_completed_stage,
            "started_at": str(
                existing_lock.get("started_at", observed_at)
                if resume_loop else observed_at
            ),
            "updated_at": observed_at,
            "paper_only": True,
        })
        loop_started = True
        callbacks = stage_callbacks or {}
        started = time.perf_counter()

        try:
            resume_after = (
                STAGES.index(last_completed_stage) + 1
                if last_completed_stage in STAGES else 0
            )

            for stage_name in STAGES[resume_after:]:
                stage_started = time.perf_counter()
                callback_result = (
                    callbacks[stage_name]()
                    if stage_name in callbacks
                    else {
                        "status": "PASS",
                        "mode": "LOCAL_INTEGRATION_PLAN_ONLY",
                    }
                )
                stage_status = str(
                    callback_result.get("status", "PASS")
                )
                stage_record = {
                    "stage": stage_name,
                    "status": stage_status,
                    "elapsed_ms": round(
                        (time.perf_counter() - stage_started) * 1000,
                        3,
                    ),
                }
                stage_results.append(stage_record)

                if stage_status not in {"PASS", "NO_ACTION", "REJECTED"}:
                    raise RuntimeError(
                        f"{stage_name} stage returned {stage_status}"
                    )

                last_completed_stage = stage_name
                write_json(loop_lock_path, {
                    "stage": "V82.30",
                    "active": True,
                    "completed": False,
                    "loop_id": current_loop_id,
                    "session_id": session_id,
                    "tick_id": tick_id,
                    "last_completed_stage": last_completed_stage,
                    "started_at": str(
                        existing_lock.get("started_at", observed_at)
                        if resume_loop else observed_at
                    ),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "paper_only": True,
                })

            loop_completed = True
            finished_at = datetime.now(timezone.utc).isoformat()
            elapsed_ms = round(
                (time.perf_counter() - started) * 1000,
                3,
            )
            append_jsonl(loop_ledger_path, {
                "stage": "V82.31",
                "event": "INTRADAY_LOOP_COMPLETED",
                "loop_id": current_loop_id,
                "session_id": session_id,
                "tick_id": tick_id,
                "started_at": observed_at,
                "finished_at": finished_at,
                "elapsed_ms": elapsed_ms,
                "recovered": loop_recovered,
                "stages": stage_results,
                "paper_only": True,
            })
            ledger_written = True
            write_json(loop_lock_path, {
                "active": False,
                "completed": True,
                "loop_id": current_loop_id,
                "session_id": session_id,
                "tick_id": tick_id,
                "last_completed_stage": last_completed_stage,
                "finished_at": finished_at,
                "paper_only": True,
            })
            state, status = "INTRADAY_LOOP_COMPLETE", "PASS"

        except Exception as exc:
            issues.append({
                "code": "INTRADAY_LOOP_STAGE_FAILED",
                "blocking": True,
                "detail": str(exc),
            })
            write_json(recovery_path, {
                "stage": "V82.30",
                "recovery_available": True,
                "loop_id": current_loop_id,
                "session_id": session_id,
                "tick_id": tick_id,
                "last_completed_stage": last_completed_stage,
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "reason": str(exc),
                "paper_only": True,
            })
            recovery_written = True
            state, status = "INTRADAY_LOOP_RECOVERY_REQUIRED", "BLOCKED"

    if not recovery_written:
        write_json(recovery_path, {
            "stage": "V82.30",
            "recovery_available": (
                state == "INTRADAY_LOOP_RECOVERY_REQUIRED"
            ),
            "loop_id": current_loop_id,
            "session_id": session_id,
            "tick_id": tick_id,
            "last_completed_stage": last_completed_stage,
            "observed_at": observed_at,
            "paper_only": True,
        })
        recovery_written = True

    dashboard = {
        "stage": "V82.32",
        "loop_state": state,
        "loop_id": current_loop_id,
        "session_id": session_id,
        "tick_id": tick_id,
        "session_ready": session_ready,
        "scheduler_ready": scheduler_ready,
        "tick_authorized": tick_authorized,
        "risk_clear": risk_clear,
        "authorization_ready": authorization_ready,
        "loop_started": loop_started,
        "loop_completed": loop_completed,
        "loop_recovered": loop_recovered,
        "last_completed_stage": last_completed_stage,
        "stage_count": len(stage_results),
        "gate_reasons": gate_reasons,
        "paper_only": True,
        "read_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "observed_at": observed_at,
    }
    write_json(dashboard_path, dashboard)

    result = {
        "stage_range": "V82.29-V82.32",
        "implementation_type": "INTRADAY_PAPER_LOOP_MANAGER_FOUNDATION",
        "status": status,
        "state": state,
        "loop_id": current_loop_id,
        "session_id": session_id,
        "tick_id": tick_id,
        "execute_loop_requested": execute_loop,
        "resume_loop_requested": resume_loop,
        "session_ready": session_ready,
        "scheduler_ready": scheduler_ready,
        "tick_authorized": tick_authorized,
        "risk_clear": risk_clear,
        "authorization_ready": authorization_ready,
        "gate_reasons": gate_reasons,
        "active_loop": active_loop,
        "duplicate_loop": duplicate_loop,
        "recovery_available": recovery_available,
        "loop_started": loop_started,
        "loop_completed": loop_completed,
        "loop_recovered": loop_recovered,
        "last_completed_stage": last_completed_stage,
        "stage_count": len(stage_results),
        "stage_results": stage_results,
        "loop_ledger_written": ledger_written,
        "recovery_snapshot_written": recovery_written,
        "dashboard_state_written": True,
        "single_loop_only": True,
        "continuous_loop_enabled": False,
        "windows_task_install_enabled": False,
        "paper_only": True,
        "read_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "cancel_enabled": False,
        "replace_enabled": False,
        "position_close_enabled": False,
        "live_trading_enabled": False,
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "actual_paper_orders_submitted": 0,
        "live_orders_submitted": 0,
        "issue_count": len(issues),
        "blocking_issue_count": sum(
            1 for item in issues if item.get("blocking")
        ),
        "issues": issues,
        "next_phase": (
            "V82_33_END_OF_DAY_MANAGER"
            if state in {
                "INTRADAY_LOOP_READY",
                "INTRADAY_LOOP_COMPLETE",
            }
            else "V82_29_TO_V82_32_WAIT_OR_RECOVER"
        ),
        "validation_mode": "LOCAL_INTRADAY_LOOP_ONLY",
        "observed_at": observed_at,
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
