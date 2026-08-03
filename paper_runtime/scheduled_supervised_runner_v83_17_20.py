
from __future__ import annotations

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
        if line.strip():
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


def evaluate_schedule_gate(
    *,
    observed_at: datetime,
    market_calendar: dict[str, Any],
    risk_result: dict[str, Any],
    supervised_result: dict[str, Any],
    policy: dict[str, Any],
    run_history: list[dict[str, Any]],
) -> dict[str, Any]:
    reasons: list[str] = []

    trading_date = observed_at.date().isoformat()
    market_open = bool(market_calendar.get("market_open", False))
    market_closed = bool(market_calendar.get("market_closed", False))
    trading_day = bool(market_calendar.get("trading_day", True))
    risk_clear = risk_result.get("state") == "SHADOW_RISK_CLEAR"

    start = parse_hhmm(str(policy.get("window_start_utc", "13:30")))
    end = parse_hhmm(str(policy.get("window_end_utc", "20:00")))
    in_window = within_window(observed_at.time().replace(tzinfo=None), start, end)

    max_runs = int(policy.get("max_runs_per_day", 3) or 3)
    minimum_interval_seconds = int(
        policy.get("minimum_interval_seconds", 300) or 300
    )

    todays_runs = [
        row for row in run_history
        if str(row.get("trading_date", "")) == trading_date
        and row.get("event") == "SCHEDULED_RUN_AUTHORIZED"
    ]
    runs_today = len(todays_runs)

    cooldown_clear = True
    if todays_runs:
        latest = max(
            datetime.fromisoformat(str(row["authorized_at"]))
            for row in todays_runs
        )
        cooldown_clear = (
            observed_at - latest
        ).total_seconds() >= minimum_interval_seconds

    supervised_ready = supervised_result.get("state") in {
        "SUPERVISED_RUNNER_READY",
        "SUPERVISED_RUNNER_COMPLETE",
    }

    if not trading_day:
        reasons.append("NOT_TRADING_DAY")
    if not market_open or market_closed:
        reasons.append("MARKET_NOT_OPEN")
    if not in_window:
        reasons.append("OUTSIDE_ALLOWED_TIME_WINDOW")
    if not risk_clear:
        reasons.append("RISK_NOT_CLEAR")
    if not supervised_ready:
        reasons.append("SUPERVISED_RUNNER_NOT_READY")
    if runs_today >= max_runs:
        reasons.append("DAILY_RUN_LIMIT_REACHED")
    if not cooldown_clear:
        reasons.append("MINIMUM_RUN_INTERVAL_NOT_MET")

    return {
        "trading_date": trading_date,
        "trading_day": trading_day,
        "market_open": market_open,
        "market_closed": market_closed,
        "risk_clear": risk_clear,
        "supervised_ready": supervised_ready,
        "in_allowed_window": in_window,
        "runs_today": runs_today,
        "max_runs_per_day": max_runs,
        "cooldown_clear": cooldown_clear,
        "minimum_interval_seconds": minimum_interval_seconds,
        "schedule_ready": len(reasons) == 0,
        "schedule_reasons": reasons,
    }


def run_scheduled_supervised_runner(
    *,
    market_calendar_path: Path,
    risk_result_path: Path,
    supervised_result_path: Path,
    policy_path: Path,
    schedule_lock_path: Path,
    schedule_ledger_path: Path,
    authorization_path: Path,
    dashboard_path: Path,
    result_path: Path,
    authorize_run: bool = False,
    complete_run: bool = False,
    clear_schedule_lock: bool = False,
    observed_at_override: str = "",
) -> dict[str, Any]:
    observed_at = (
        datetime.fromisoformat(observed_at_override)
        if observed_at_override
        else datetime.now(timezone.utc)
    )
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    now_iso = observed_at.isoformat()

    issues: list[dict[str, Any]] = []
    inputs: dict[str, dict[str, Any]] = {}
    for name, path in {
        "market_calendar": market_calendar_path,
        "risk": risk_result_path,
        "supervised": supervised_result_path,
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
            "code": "SCHEDULE_POLICY_NOT_FOUND",
            "blocking": True,
            "detail": str(policy_path),
        })

    checks = (
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
            "CONTINUOUS_LOOP_MUST_BE_DISABLED",
            not bool(policy.get("continuous_loop_enabled", True)),
        ),
    )
    for code, passed in checks:
        if not passed:
            issues.append({
                "code": code,
                "blocking": True,
                "detail": "scheduled runner safety policy failed",
            })

    history = load_jsonl(schedule_ledger_path)
    evaluation = evaluate_schedule_gate(
        observed_at=observed_at,
        market_calendar=inputs["market_calendar"],
        risk_result=inputs["risk"],
        supervised_result=inputs["supervised"],
        policy=policy,
        run_history=history,
    )

    lock = load_json(schedule_lock_path)
    active_schedule = bool(lock.get("active", False))
    duplicate_authorization = authorize_run and active_schedule
    if duplicate_authorization:
        issues.append({
            "code": "DUPLICATE_SCHEDULE_AUTHORIZATION_BLOCKED",
            "blocking": True,
            "detail": str(lock.get("authorization_id", "")),
        })

    blocking = any(item.get("blocking") for item in issues)
    authorization_written = False
    schedule_lock_written = False
    schedule_ledger_written = False
    run_authorized = False
    run_completed = False
    authorization_id = str(lock.get("authorization_id", ""))

    if blocking:
        state, status = "SCHEDULED_RUNNER_SAFE_MODE", "BLOCKED"

    elif clear_schedule_lock:
        write_json(schedule_lock_path, {
            "active": False,
            "authorization_id": "",
            "cleared_at": now_iso,
            "paper_only": True,
        })
        schedule_lock_written = True
        state, status = "SCHEDULE_LOCK_CLEARED", "PASS"

    elif complete_run:
        if active_schedule:
            authorization_id = str(lock.get("authorization_id", ""))
            append_jsonl(schedule_ledger_path, {
                "stage": "V83.19",
                "event": "SCHEDULED_RUN_COMPLETED",
                "authorization_id": authorization_id,
                "trading_date": evaluation["trading_date"],
                "completed_at": now_iso,
                "paper_only": True,
            })
            write_json(schedule_lock_path, {
                "active": False,
                "authorization_id": authorization_id,
                "completed_at": now_iso,
                "paper_only": True,
            })
            schedule_lock_written = True
            schedule_ledger_written = True
            run_completed = True
            state, status = "SCHEDULED_RUN_COMPLETED", "PASS"
        else:
            state, status = "NO_ACTIVE_SCHEDULED_RUN", "PASS"

    elif authorize_run:
        if evaluation["schedule_ready"]:
            authorization_id = (
                "scheduled-run-"
                + observed_at.strftime("%Y%m%d%H%M%S%f")
            )
            authorization = {
                "stage": "V83.18",
                "authorization_id": authorization_id,
                "trading_date": evaluation["trading_date"],
                "authorized_at": now_iso,
                "expires_at_window_end_utc": str(
                    policy.get("window_end_utc", "20:00")
                ),
                "max_supervised_cycles": int(
                    policy.get("max_supervised_cycles_per_run", 3) or 3
                ),
                "execute_supervised_runner": True,
                "windows_task_install_enabled": False,
                "paper_only": True,
            }
            write_json(authorization_path, authorization)
            write_json(schedule_lock_path, {
                "active": True,
                "authorization_id": authorization_id,
                "trading_date": evaluation["trading_date"],
                "authorized_at": now_iso,
                "paper_only": True,
            })
            append_jsonl(schedule_ledger_path, {
                **authorization,
                "event": "SCHEDULED_RUN_AUTHORIZED",
            })
            authorization_written = True
            schedule_lock_written = True
            schedule_ledger_written = True
            run_authorized = True
            state, status = "SCHEDULED_RUN_AUTHORIZED", "PASS"
        else:
            state, status = "SCHEDULED_RUN_WAIT_GATES", "PASS"

    else:
        if active_schedule:
            state, status = "SCHEDULED_RUN_IN_PROGRESS", "PASS"
        elif evaluation["schedule_ready"]:
            state, status = "SCHEDULED_RUN_READY", "PASS"
        else:
            state, status = "SCHEDULED_RUN_WAIT_GATES", "PASS"

    dashboard = {
        "stage": "V83.20",
        "scheduled_runner_state": state,
        "authorization_id": authorization_id,
        "active_schedule": active_schedule or run_authorized,
        "run_authorized": run_authorized,
        "run_completed": run_completed,
        **evaluation,
        "operator_supervision_required": True,
        "windows_task_install_enabled": False,
        "continuous_loop_enabled": False,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "paper_only": True,
        "observed_at": now_iso,
    }
    write_json(dashboard_path, dashboard)

    result = {
        "stage_range": "V83.17-V83.20",
        "implementation_type": "SCHEDULED_SUPERVISED_RUNNER_FOUNDATION",
        "status": status,
        "state": state,
        "authorization_id": authorization_id,
        "authorize_run_requested": authorize_run,
        "complete_run_requested": complete_run,
        "clear_schedule_lock_requested": clear_schedule_lock,
        "active_schedule": active_schedule or run_authorized,
        "duplicate_authorization": duplicate_authorization,
        "run_authorized": run_authorized,
        "run_completed": run_completed,
        **evaluation,
        "authorization_written": authorization_written,
        "schedule_lock_written": schedule_lock_written,
        "schedule_ledger_written": schedule_ledger_written,
        "dashboard_state_written": True,
        "operator_supervision_required": True,
        "automatic_scheduling_enabled": False,
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
            "V83_21_SCHEDULED_RUN_DISPATCH"
            if state in {
                "SCHEDULED_RUN_READY",
                "SCHEDULED_RUN_AUTHORIZED",
                "SCHEDULED_RUN_COMPLETED",
                "SCHEDULED_RUN_WAIT_GATES",
            }
            else "V83_17_TO_V83_20_WAIT_OR_RECOVER"
        ),
        "validation_mode": "LOCAL_SCHEDULE_GATE_ONLY",
        "observed_at": now_iso,
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
