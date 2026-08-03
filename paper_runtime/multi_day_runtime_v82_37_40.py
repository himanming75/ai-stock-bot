
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
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


def next_trading_date(
    current_date: str,
    holidays: set[str],
) -> str:
    candidate = date.fromisoformat(current_date) + timedelta(days=1)
    while candidate.weekday() >= 5 or candidate.isoformat() in holidays:
        candidate += timedelta(days=1)
    return candidate.isoformat()


def runtime_id(
    previous_trading_date: str,
    next_date: str,
) -> str:
    raw = f"{previous_trading_date}|{next_date}".encode("utf-8")
    return "multi-day-runtime-" + hashlib.sha256(raw).hexdigest()[:20]


def run_multi_day_runtime(
    *,
    end_of_day_result_path: Path,
    certification_path: Path,
    next_day_state_path: Path,
    policy_path: Path,
    runtime_state_path: Path,
    rollover_lock_path: Path,
    runtime_ledger_path: Path,
    rollover_plan_path: Path,
    dashboard_path: Path,
    result_path: Path,
    execute_rollover: bool = False,
    reset_runtime: bool = False,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    issues: list[dict[str, Any]] = []

    try:
        end_of_day = load_json(end_of_day_result_path)
    except Exception as exc:
        end_of_day = {}
        issues.append({
            "code": "INVALID_END_OF_DAY_RESULT",
            "blocking": True,
            "detail": str(exc),
        })

    try:
        certification = load_json(certification_path)
    except Exception as exc:
        certification = {}
        issues.append({
            "code": "INVALID_DAILY_CERTIFICATION",
            "blocking": True,
            "detail": str(exc),
        })

    try:
        next_day_state = load_json(next_day_state_path)
    except Exception as exc:
        next_day_state = {}
        issues.append({
            "code": "INVALID_NEXT_DAY_STATE",
            "blocking": True,
            "detail": str(exc),
        })

    try:
        policy = load_json(policy_path)
    except Exception as exc:
        policy = {}
        issues.append({
            "code": "INVALID_MULTI_DAY_POLICY",
            "blocking": True,
            "detail": str(exc),
        })

    if not policy:
        issues.append({
            "code": "MULTI_DAY_POLICY_NOT_FOUND",
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
            "AUTOMATIC_SESSION_START_MUST_BE_DISABLED",
            not bool(policy.get("automatic_session_start_enabled", True)),
        ),
    )
    for code, passed in safety_checks:
        if not passed:
            issues.append({
                "code": code,
                "blocking": True,
                "detail": "multi-day safety policy failed",
            })

    runtime_state = load_json(runtime_state_path)
    rollover_lock = load_json(rollover_lock_path)
    ledger = load_jsonl(runtime_ledger_path)

    previous_trading_date = str(
        certification.get(
            "trading_date",
            end_of_day.get("trading_date", ""),
        )
    )
    day_certified = bool(certification.get("certified", False))
    next_day_prepared = bool(next_day_state.get("next_day_ready", False))

    holidays = {
        str(item)
        for item in policy.get("market_holidays", [])
    }

    calculated_next_date = (
        next_trading_date(previous_trading_date, holidays)
        if previous_trading_date else ""
    )

    expected_next_date = str(
        next_day_state.get("next_trading_date", calculated_next_date)
        or calculated_next_date
    )

    rollover_ready = (
        day_certified
        and next_day_prepared
        and bool(previous_trading_date)
        and bool(expected_next_date)
    )

    duplicate_rollover = (
        execute_rollover
        and bool(rollover_lock.get("active", False))
    )
    if duplicate_rollover:
        issues.append({
            "code": "DUPLICATE_ROLLOVER_BLOCKED",
            "blocking": True,
            "detail": str(rollover_lock.get("runtime_id", "")),
        })

    existing_dates = {
        str(row.get("next_trading_date", ""))
        for row in ledger
        if row.get("event") == "ROLLOVER_COMPLETED"
    }
    already_completed = expected_next_date in existing_dates
    if execute_rollover and already_completed:
        issues.append({
            "code": "ROLLOVER_ALREADY_COMPLETED",
            "blocking": True,
            "detail": expected_next_date,
        })

    blocking = any(item.get("blocking") for item in issues)

    runtime_started = False
    rollover_completed = False
    runtime_reset = False
    ledger_written = False
    rollover_plan_written = False
    runtime_state_written = False
    lock_written = False

    current_runtime_id = str(runtime_state.get("runtime_id", ""))
    completed_days = int(runtime_state.get("completed_days", 0) or 0)
    current_trading_date = str(
        runtime_state.get("current_trading_date", previous_trading_date)
    )

    if blocking:
        state, status = "MULTI_DAY_RUNTIME_SAFE_MODE", "BLOCKED"

    elif reset_runtime:
        reset_payload = {
            "stage": "V82.40",
            "runtime_id": "",
            "runtime_active": False,
            "completed_days": 0,
            "current_trading_date": "",
            "next_trading_date": "",
            "last_rollover_at": "",
            "paper_only": True,
            "reset_at": now_iso,
        }
        write_json(runtime_state_path, reset_payload)
        write_json(rollover_lock_path, {
            "active": False,
            "runtime_id": "",
            "reset_at": now_iso,
            "paper_only": True,
        })
        runtime_state_written = True
        lock_written = True
        runtime_reset = True
        state, status = "MULTI_DAY_RUNTIME_RESET", "PASS"

    elif execute_rollover:
        if rollover_ready:
            current_runtime_id = (
                str(runtime_state.get("runtime_id", ""))
                or runtime_id(
                    previous_trading_date,
                    expected_next_date,
                )
            )

            write_json(rollover_lock_path, {
                "stage": "V82.38",
                "active": True,
                "runtime_id": current_runtime_id,
                "previous_trading_date": previous_trading_date,
                "next_trading_date": expected_next_date,
                "created_at": now_iso,
                "paper_only": True,
            })
            lock_written = True

            rollover_plan = {
                "stage": "V82.38-V82.39",
                "runtime_id": current_runtime_id,
                "previous_trading_date": previous_trading_date,
                "next_trading_date": expected_next_date,
                "session_reset_required": True,
                "scheduler_reset_required": True,
                "intraday_loop_reset_required": True,
                "risk_refresh_required": True,
                "authorization_refresh_required": True,
                "automatic_session_start_enabled": False,
                "paper_only": True,
                "created_at": now_iso,
            }
            write_json(rollover_plan_path, rollover_plan)
            rollover_plan_written = True

            completed_days += 1
            current_trading_date = expected_next_date
            runtime_payload = {
                "stage": "V82.37-V82.40",
                "runtime_id": current_runtime_id,
                "runtime_active": True,
                "completed_days": completed_days,
                "previous_trading_date": previous_trading_date,
                "current_trading_date": current_trading_date,
                "next_trading_date": next_trading_date(
                    current_trading_date,
                    holidays,
                ),
                "last_rollover_at": now_iso,
                "paper_only": True,
                "broker_write_enabled": False,
                "order_submission_enabled": False,
                "automatic_session_start_enabled": False,
            }
            write_json(runtime_state_path, runtime_payload)
            runtime_state_written = True

            append_jsonl(runtime_ledger_path, {
                "stage": "V82.39",
                "event": "ROLLOVER_COMPLETED",
                "runtime_id": current_runtime_id,
                "completed_days": completed_days,
                "previous_trading_date": previous_trading_date,
                "next_trading_date": expected_next_date,
                "completed_at": now_iso,
                "paper_only": True,
            })
            ledger_written = True

            write_json(rollover_lock_path, {
                "active": False,
                "runtime_id": current_runtime_id,
                "previous_trading_date": previous_trading_date,
                "next_trading_date": expected_next_date,
                "completed_at": now_iso,
                "paper_only": True,
            })
            lock_written = True

            runtime_started = True
            rollover_completed = True
            state, status = "MULTI_DAY_ROLLOVER_COMPLETE", "PASS"
        else:
            state, status = "MULTI_DAY_RUNTIME_WAIT_GATES", "PASS"

    else:
        if rollover_ready:
            state, status = "MULTI_DAY_ROLLOVER_READY", "PASS"
        elif day_certified and not next_day_prepared:
            state, status = "WAIT_NEXT_DAY_PREPARATION", "PASS"
        elif not day_certified:
            state, status = "WAIT_DAILY_CERTIFICATION", "PASS"
        else:
            state, status = "MULTI_DAY_RUNTIME_WAIT_GATES", "PASS"

    dashboard = {
        "stage": "V82.40",
        "multi_day_state": state,
        "runtime_id": current_runtime_id,
        "runtime_active": bool(
            runtime_state.get("runtime_active", False)
        ) or rollover_completed,
        "completed_days": completed_days,
        "previous_trading_date": previous_trading_date,
        "current_trading_date": current_trading_date,
        "next_trading_date": expected_next_date,
        "day_certified": day_certified,
        "next_day_prepared": next_day_prepared,
        "rollover_ready": rollover_ready,
        "rollover_completed": rollover_completed,
        "automatic_session_start_enabled": False,
        "paper_only": True,
        "read_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "observed_at": now_iso,
    }
    write_json(dashboard_path, dashboard)

    result = {
        "stage_range": "V82.37-V82.40",
        "implementation_type": (
            "MULTI_DAY_PAPER_RUNTIME_AND_NEXT_DAY_ROLLOVER"
        ),
        "status": status,
        "state": state,
        "runtime_id": current_runtime_id,
        "runtime_started": runtime_started,
        "runtime_reset": runtime_reset,
        "completed_days": completed_days,
        "previous_trading_date": previous_trading_date,
        "current_trading_date": current_trading_date,
        "next_trading_date": expected_next_date,
        "day_certified": day_certified,
        "next_day_prepared": next_day_prepared,
        "rollover_ready": rollover_ready,
        "execute_rollover_requested": execute_rollover,
        "rollover_completed": rollover_completed,
        "duplicate_rollover": duplicate_rollover,
        "already_completed": already_completed,
        "runtime_state_written": runtime_state_written,
        "rollover_lock_written": lock_written,
        "rollover_plan_written": rollover_plan_written,
        "runtime_ledger_written": ledger_written,
        "dashboard_state_written": True,
        "automatic_session_start_enabled": False,
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
            "V83_01_AUTOMATED_PAPER_RUNTIME_ORCHESTRATOR"
            if state in {
                "MULTI_DAY_ROLLOVER_READY",
                "MULTI_DAY_ROLLOVER_COMPLETE",
            }
            else "V82_37_TO_V82_40_WAIT_OR_RECOVER"
        ),
        "validation_mode": "LOCAL_MULTI_DAY_RUNTIME_ONLY",
        "observed_at": now_iso,
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
