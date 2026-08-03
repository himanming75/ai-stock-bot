
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


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


def parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def tick_id(session_id: str, scheduled_for: str) -> str:
    raw = f"{session_id}|{scheduled_for}".encode("utf-8")
    return "paper-tick-" + hashlib.sha256(raw).hexdigest()[:20]


def run_paper_trading_scheduler(
    *,
    session_result_path: Path,
    policy_path: Path,
    heartbeat_path: Path,
    tick_lock_path: Path,
    tick_ledger_path: Path,
    dashboard_path: Path,
    result_path: Path,
    write_heartbeat: bool = False,
    authorize_tick: bool = False,
    complete_tick: bool = False,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    now = observed_at or datetime.now(timezone.utc)
    now_iso = now.isoformat()
    issues: list[dict[str, Any]] = []

    try:
        session = load_json(session_result_path)
    except Exception as exc:
        session = {}
        issues.append({
            "code": "INVALID_SESSION_RESULT",
            "blocking": True,
            "detail": str(exc),
        })

    try:
        policy = load_json(policy_path)
    except Exception as exc:
        policy = {}
        issues.append({
            "code": "INVALID_SCHEDULER_POLICY",
            "blocking": True,
            "detail": str(exc),
        })

    if not policy:
        issues.append({
            "code": "SCHEDULER_POLICY_NOT_FOUND",
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
                "detail": "scheduler safety policy failed",
            })

    interval_seconds = int(policy.get("interval_seconds", 300))
    heartbeat_timeout_seconds = int(
        policy.get("heartbeat_timeout_seconds", 900)
    )
    maximum_lateness_seconds = int(
        policy.get("maximum_lateness_seconds", 120)
    )

    if interval_seconds < 1:
        issues.append({
            "code": "INVALID_INTERVAL_SECONDS",
            "blocking": True,
            "detail": str(interval_seconds),
        })

    session_active = bool(session.get("session_active", False))
    session_running = session.get("state") == "PAPER_SESSION_RUNNING"
    session_ready = session_active and session_running
    session_id = str(session.get("session_id", ""))

    heartbeat = load_json(heartbeat_path)
    heartbeat_written = False
    if write_heartbeat:
        heartbeat = {
            "stage": "V82.26",
            "session_id": session_id,
            "last_heartbeat_at": now_iso,
            "scheduler_active": session_ready,
            "paper_only": True,
        }
        write_json(heartbeat_path, heartbeat)
        heartbeat_written = True

    heartbeat_age_seconds: float | None = None
    heartbeat_timeout = False
    if heartbeat.get("last_heartbeat_at"):
        heartbeat_time = parse_iso(str(heartbeat["last_heartbeat_at"]))
        heartbeat_age_seconds = max(
            0.0,
            (now - heartbeat_time).total_seconds(),
        )
        heartbeat_timeout = (
            heartbeat_age_seconds > heartbeat_timeout_seconds
        )

    last_tick_at_text = str(
        heartbeat.get(
            "last_tick_completed_at",
            session.get("started_at", session.get("observed_at", now_iso)),
        )
    )
    last_tick_at = parse_iso(last_tick_at_text)
    next_tick_at = last_tick_at + timedelta(seconds=interval_seconds)
    tick_due = now >= next_tick_at
    lateness_seconds = max(
        0.0,
        (now - next_tick_at).total_seconds(),
    )
    tick_late = (
        tick_due and lateness_seconds > maximum_lateness_seconds
    )

    tick_lock = load_json(tick_lock_path)
    active_tick = bool(tick_lock.get("active", False))
    duplicate_tick = authorize_tick and active_tick
    if duplicate_tick:
        issues.append({
            "code": "DUPLICATE_TICK_BLOCKED",
            "blocking": True,
            "detail": str(tick_lock.get("tick_id", "")),
        })

    blocking = any(item.get("blocking") for item in issues)
    authorized = False
    tick_completed = False
    tick_lock_written = False
    tick_ledger_written = False
    current_tick_id = str(tick_lock.get("tick_id", ""))

    if blocking:
        state, status = "PAPER_SCHEDULER_SAFE_MODE", "BLOCKED"
    elif not session_ready:
        state, status = "WAIT_PAPER_SESSION_RUNNING", "PASS"
    elif heartbeat_timeout:
        state, status = "PAPER_SCHEDULER_HEARTBEAT_TIMEOUT", "PASS"
    elif complete_tick:
        if active_tick:
            current_tick_id = str(tick_lock.get("tick_id", ""))
            write_json(tick_lock_path, {
                "active": False,
                "tick_id": current_tick_id,
                "session_id": session_id,
                "completed_at": now_iso,
                "paper_only": True,
            })
            heartbeat["last_tick_completed_at"] = now_iso
            heartbeat["last_heartbeat_at"] = now_iso
            heartbeat["session_id"] = session_id
            heartbeat["scheduler_active"] = True
            heartbeat["paper_only"] = True
            write_json(heartbeat_path, heartbeat)
            append_jsonl(tick_ledger_path, {
                "stage": "V82.27",
                "event": "TICK_COMPLETED",
                "tick_id": current_tick_id,
                "session_id": session_id,
                "completed_at": now_iso,
                "paper_only": True,
            })
            tick_completed = True
            tick_lock_written = True
            tick_ledger_written = True
            state, status = "PAPER_SCHEDULER_TICK_COMPLETED", "PASS"
        else:
            state, status = "PAPER_SCHEDULER_NO_ACTIVE_TICK", "PASS"
    elif tick_late:
        state, status = "PAPER_SCHEDULER_TICK_LATE", "PASS"
    elif not tick_due:
        state, status = "PAPER_SCHEDULER_WAIT_INTERVAL", "PASS"
    elif authorize_tick:
        scheduled_for = next_tick_at.isoformat()
        current_tick_id = tick_id(session_id, scheduled_for)
        write_json(tick_lock_path, {
            "stage": "V82.27",
            "active": True,
            "tick_id": current_tick_id,
            "session_id": session_id,
            "scheduled_for": scheduled_for,
            "authorized_at": now_iso,
            "paper_only": True,
        })
        append_jsonl(tick_ledger_path, {
            "stage": "V82.27",
            "event": "TICK_AUTHORIZED",
            "tick_id": current_tick_id,
            "session_id": session_id,
            "scheduled_for": scheduled_for,
            "authorized_at": now_iso,
            "lateness_seconds": round(lateness_seconds, 3),
            "paper_only": True,
        })
        authorized = True
        tick_lock_written = True
        tick_ledger_written = True
        state, status = "PAPER_SCHEDULER_TICK_AUTHORIZED", "PASS"
    else:
        state, status = "PAPER_SCHEDULER_TICK_DUE", "PASS"

    dashboard = {
        "stage": "V82.28",
        "scheduler_state": state,
        "session_id": session_id,
        "session_ready": session_ready,
        "interval_seconds": interval_seconds,
        "heartbeat_age_seconds": (
            round(heartbeat_age_seconds, 3)
            if heartbeat_age_seconds is not None else None
        ),
        "heartbeat_timeout": heartbeat_timeout,
        "tick_due": tick_due,
        "tick_late": tick_late,
        "next_tick_at": next_tick_at.isoformat(),
        "tick_id": current_tick_id,
        "tick_authorized": authorized,
        "active_tick": active_tick or authorized,
        "paper_only": True,
        "read_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "observed_at": now_iso,
    }
    write_json(dashboard_path, dashboard)

    result = {
        "stage_range": "V82.25-V82.28",
        "implementation_type": "PAPER_TRADING_SCHEDULER_FOUNDATION",
        "status": status,
        "state": state,
        "session_id": session_id,
        "session_ready": session_ready,
        "interval_seconds": interval_seconds,
        "heartbeat_timeout_seconds": heartbeat_timeout_seconds,
        "maximum_lateness_seconds": maximum_lateness_seconds,
        "heartbeat_requested": write_heartbeat,
        "heartbeat_written": heartbeat_written,
        "heartbeat_age_seconds": (
            round(heartbeat_age_seconds, 3)
            if heartbeat_age_seconds is not None else None
        ),
        "heartbeat_timeout": heartbeat_timeout,
        "tick_due": tick_due,
        "tick_late": tick_late,
        "lateness_seconds": round(lateness_seconds, 3),
        "next_tick_at": next_tick_at.isoformat(),
        "authorize_tick_requested": authorize_tick,
        "complete_tick_requested": complete_tick,
        "tick_id": current_tick_id,
        "tick_authorized": authorized,
        "tick_completed": tick_completed,
        "active_tick": active_tick or authorized,
        "duplicate_tick": duplicate_tick,
        "tick_lock_written": tick_lock_written,
        "tick_ledger_written": tick_ledger_written,
        "dashboard_state_written": True,
        "single_tick_only": True,
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
            "V82_29_INTRADAY_LOOP_MANAGER"
            if state in {
                "PAPER_SCHEDULER_WAIT_INTERVAL",
                "PAPER_SCHEDULER_TICK_DUE",
                "PAPER_SCHEDULER_TICK_AUTHORIZED",
                "PAPER_SCHEDULER_TICK_COMPLETED",
            }
            else "V82_25_TO_V82_28_WAIT_OR_RECOVER"
        ),
        "validation_mode": "LOCAL_PAPER_SCHEDULER_ONLY",
        "observed_at": now_iso,
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
