
from __future__ import annotations

import hashlib
import json
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if isinstance(value, dict):
            rows.append(value)
    return rows


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


def parse_hhmm(value: str) -> time:
    hour, minute = [int(part) for part in value.split(":", 1)]
    return time(hour=hour, minute=minute)


def within_window(current: time, start: time, end: time) -> bool:
    if start <= end:
        return start <= current <= end
    return current >= start or current <= end


def trigger_id(observed_at: str, trading_date: str) -> str:
    raw = f"{observed_at}|{trading_date}".encode("utf-8")
    return "local-trigger-" + hashlib.sha256(raw).hexdigest()[:20]


def evaluate_automatic_schedule(
    *,
    observed_at: datetime,
    session_result: dict[str, Any],
    risk_result: dict[str, Any],
    supervised_result: dict[str, Any],
    schedule_result: dict[str, Any],
    policy: dict[str, Any],
    trigger_history: list[dict[str, Any]],
) -> dict[str, Any]:
    reasons: list[str] = []

    trading_day = bool(
        session_result.get(
            "trading_day",
            session_result.get("market_open", False),
        )
    )
    market_open = bool(session_result.get("market_open", False))
    market_closed = bool(session_result.get("market_closed", False))
    session_active = bool(session_result.get("session_active", False))
    risk_clear = risk_result.get("state") == "SHADOW_RISK_CLEAR"
    supervised_ready = supervised_result.get("state") in {
        "SUPERVISED_RUNNER_READY",
        "SUPERVISED_RUNNER_COMPLETE",
    }
    schedule_idle = schedule_result.get("state") in {
        "SCHEDULED_RUN_READY",
        "SCHEDULED_RUN_WAIT_GATES",
        "SCHEDULED_RUN_COMPLETED",
        "SCHEDULE_LOCK_CLEARED",
        "",
    }

    start = parse_hhmm(str(policy.get("window_start_utc", "13:30")))
    end = parse_hhmm(str(policy.get("window_end_utc", "20:00")))
    current_time = observed_at.time().replace(tzinfo=None)
    in_window = within_window(current_time, start, end)

    trading_date = observed_at.date().isoformat()
    max_triggers = int(policy.get("max_triggers_per_day", 3) or 3)
    cooldown_seconds = int(
        policy.get("minimum_trigger_interval_seconds", 300) or 300
    )

    today_triggers = [
        row
        for row in trigger_history
        if row.get("event") == "LOCAL_TRIGGER_CREATED"
        and str(row.get("trading_date", "")) == trading_date
    ]
    triggers_today = len(today_triggers)

    cooldown_clear = True
    if today_triggers:
        latest = max(
            datetime.fromisoformat(str(row["created_at"]))
            for row in today_triggers
        )
        cooldown_clear = (
            observed_at - latest
        ).total_seconds() >= cooldown_seconds

    if not trading_day:
        reasons.append("NOT_TRADING_DAY")
    if not market_open or market_closed:
        reasons.append("MARKET_NOT_OPEN")
    if session_active:
        reasons.append("SESSION_ALREADY_ACTIVE")
    if not in_window:
        reasons.append("OUTSIDE_ALLOWED_WINDOW")
    if not risk_clear:
        reasons.append("RISK_NOT_CLEAR")
    if not supervised_ready:
        reasons.append("SUPERVISED_RUNNER_NOT_READY")
    if not schedule_idle:
        reasons.append("SCHEDULE_PIPELINE_NOT_IDLE")
    if triggers_today >= max_triggers:
        reasons.append("DAILY_TRIGGER_LIMIT_REACHED")
    if not cooldown_clear:
        reasons.append("TRIGGER_COOLDOWN_NOT_MET")

    return {
        "trading_date": trading_date,
        "trading_day": trading_day,
        "market_open": market_open,
        "market_closed": market_closed,
        "session_active": session_active,
        "risk_clear": risk_clear,
        "supervised_ready": supervised_ready,
        "schedule_idle": schedule_idle,
        "in_allowed_window": in_window,
        "triggers_today": triggers_today,
        "max_triggers_per_day": max_triggers,
        "cooldown_clear": cooldown_clear,
        "minimum_trigger_interval_seconds": cooldown_seconds,
        "trigger_ready": len(reasons) == 0,
        "trigger_reasons": reasons,
    }


def run_automatic_schedule_evaluation(
    *,
    session_result_path: Path,
    risk_result_path: Path,
    supervised_result_path: Path,
    schedule_result_path: Path,
    policy_path: Path,
    trigger_lock_path: Path,
    trigger_ledger_path: Path,
    trigger_plan_path: Path,
    dashboard_path: Path,
    result_path: Path,
    create_trigger: bool = False,
    complete_trigger: bool = False,
    clear_trigger_lock: bool = False,
    observed_at_override: str = "",
) -> dict[str, Any]:
    observed_at = (
        datetime.fromisoformat(observed_at_override)
        if observed_at_override
        else datetime.now(timezone.utc)
    )
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)

    observed_iso = observed_at.isoformat()
    issues: list[dict[str, Any]] = []
    inputs: dict[str, dict[str, Any]] = {}

    for name, path in {
        "session": session_result_path,
        "risk": risk_result_path,
        "supervised": supervised_result_path,
        "schedule": schedule_result_path,
        "policy": policy_path,
    }.items():
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
            "code": "AUTOMATIC_SCHEDULE_POLICY_NOT_FOUND",
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
            "WINDOWS_TASK_INSTALL_MUST_BE_DISABLED",
            not bool(policy.get("windows_task_install_enabled", True)),
        ),
        (
            "LOCAL_TRIGGER_EXECUTION_MUST_BE_DISABLED",
            not bool(policy.get("local_trigger_execution_enabled", True)),
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
                "detail": "automatic schedule safety policy failed",
            })

    history = load_jsonl(trigger_ledger_path)
    evaluation = evaluate_automatic_schedule(
        observed_at=observed_at,
        session_result=inputs["session"],
        risk_result=inputs["risk"],
        supervised_result=inputs["supervised"],
        schedule_result=inputs["schedule"],
        policy=policy,
        trigger_history=history,
    )

    lock = load_json(trigger_lock_path)
    active_trigger = bool(lock.get("active", False))
    duplicate_trigger = create_trigger and active_trigger

    if duplicate_trigger:
        issues.append({
            "code": "DUPLICATE_LOCAL_TRIGGER_BLOCKED",
            "blocking": True,
            "detail": str(lock.get("trigger_id", "")),
        })

    blocking = any(item.get("blocking") for item in issues)
    current_trigger_id = str(lock.get("trigger_id", ""))
    trigger_created = False
    trigger_completed = False
    trigger_plan_written = False
    trigger_lock_written = False
    trigger_ledger_written = False

    if blocking:
        state, status = "AUTOMATIC_SCHEDULE_SAFE_MODE", "BLOCKED"

    elif clear_trigger_lock:
        write_json(trigger_lock_path, {
            "active": False,
            "trigger_id": "",
            "cleared_at": observed_iso,
            "paper_only": True,
        })
        trigger_lock_written = True
        state, status = "LOCAL_TRIGGER_LOCK_CLEARED", "PASS"

    elif complete_trigger:
        if active_trigger:
            current_trigger_id = str(lock.get("trigger_id", ""))
            append_jsonl(trigger_ledger_path, {
                "stage": "V83.27",
                "event": "LOCAL_TRIGGER_COMPLETED",
                "trigger_id": current_trigger_id,
                "trading_date": evaluation["trading_date"],
                "completed_at": observed_iso,
                "paper_only": True,
            })
            write_json(trigger_lock_path, {
                "active": False,
                "trigger_id": current_trigger_id,
                "completed_at": observed_iso,
                "paper_only": True,
            })
            trigger_completed = True
            trigger_lock_written = True
            trigger_ledger_written = True
            state, status = "LOCAL_TRIGGER_COMPLETED", "PASS"
        else:
            state, status = "NO_ACTIVE_LOCAL_TRIGGER", "PASS"

    elif create_trigger:
        if evaluation["trigger_ready"]:
            current_trigger_id = trigger_id(
                observed_iso,
                evaluation["trading_date"],
            )
            plan = {
                "stage": "V83.26",
                "trigger_id": current_trigger_id,
                "trading_date": evaluation["trading_date"],
                "created_at": observed_iso,
                "action": "AUTHORIZE_SCHEDULED_SUPERVISED_RUN",
                "target_script": (
                    "RUN_V83_17_TO_V83_20_"
                    "SCHEDULED_SUPERVISED_RUNNER.ps1"
                ),
                "target_arguments": ["-AuthorizeRun"],
                "local_trigger_execution_enabled": False,
                "windows_task_install_enabled": False,
                "paper_only": True,
            }
            write_json(trigger_plan_path, plan)
            write_json(trigger_lock_path, {
                "active": True,
                "trigger_id": current_trigger_id,
                "trading_date": evaluation["trading_date"],
                "created_at": observed_iso,
                "paper_only": True,
            })
            append_jsonl(trigger_ledger_path, {
                **plan,
                "event": "LOCAL_TRIGGER_CREATED",
            })
            trigger_created = True
            trigger_plan_written = True
            trigger_lock_written = True
            trigger_ledger_written = True
            state, status = "LOCAL_TRIGGER_CREATED", "PASS"
        else:
            state, status = "AUTOMATIC_SCHEDULE_WAIT_GATES", "PASS"

    else:
        if active_trigger:
            state, status = "LOCAL_TRIGGER_IN_PROGRESS", "PASS"
        elif evaluation["trigger_ready"]:
            state, status = "LOCAL_TRIGGER_READY", "PASS"
        else:
            state, status = "AUTOMATIC_SCHEDULE_WAIT_GATES", "PASS"

    dashboard = {
        "stage": "V83.28",
        "automatic_schedule_state": state,
        "trigger_id": current_trigger_id,
        "active_trigger": active_trigger or trigger_created,
        "trigger_created": trigger_created,
        "trigger_completed": trigger_completed,
        **evaluation,
        "operator_supervision_required": True,
        "automatic_scheduling_enabled": False,
        "local_trigger_execution_enabled": False,
        "windows_task_install_enabled": False,
        "continuous_loop_enabled": False,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "paper_only": True,
        "observed_at": observed_iso,
    }
    write_json(dashboard_path, dashboard)

    result = {
        "stage_range": "V83.25-V83.28",
        "implementation_type": (
            "AUTOMATIC_SCHEDULE_EVALUATION_AND_LOCAL_TRIGGER"
        ),
        "status": status,
        "state": state,
        "trigger_id": current_trigger_id,
        "create_trigger_requested": create_trigger,
        "complete_trigger_requested": complete_trigger,
        "clear_trigger_lock_requested": clear_trigger_lock,
        "active_trigger": active_trigger or trigger_created,
        "duplicate_trigger": duplicate_trigger,
        "trigger_created": trigger_created,
        "trigger_completed": trigger_completed,
        **evaluation,
        "trigger_plan_written": trigger_plan_written,
        "trigger_lock_written": trigger_lock_written,
        "trigger_ledger_written": trigger_ledger_written,
        "dashboard_state_written": True,
        "operator_supervision_required": True,
        "automatic_scheduling_enabled": False,
        "local_trigger_execution_enabled": False,
        "windows_task_install_enabled": False,
        "continuous_loop_enabled": False,
        "broker_command_execution_enabled": False,
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
            "V83_29_LOCAL_TRIGGER_DISPATCHER"
            if state in {
                "LOCAL_TRIGGER_READY",
                "LOCAL_TRIGGER_CREATED",
                "LOCAL_TRIGGER_COMPLETED",
                "AUTOMATIC_SCHEDULE_WAIT_GATES",
                "LOCAL_TRIGGER_LOCK_CLEARED",
            }
            else "V83_25_TO_V83_28_WAIT_OR_RECOVER"
        ),
        "validation_mode": "LOCAL_AUTOMATIC_SCHEDULE_EVALUATION_ONLY",
        "observed_at": observed_iso,
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
