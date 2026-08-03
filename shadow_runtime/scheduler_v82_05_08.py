
from __future__ import annotations

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


def run_shadow_scheduler(
    *,
    cycle_result_path: Path,
    policy_path: Path,
    heartbeat_path: Path,
    scheduler_lock_path: Path,
    scheduler_ledger_path: Path,
    dashboard_path: Path,
    result_path: Path,
    write_heartbeat: bool = False,
    authorize_next_cycle: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    observed = now or datetime.now(timezone.utc)
    observed_iso = observed.isoformat()

    cycle_result = load_json(cycle_result_path)
    policy = load_json(policy_path)
    heartbeat = load_json(heartbeat_path)
    scheduler_lock = load_json(scheduler_lock_path)

    issues: list[dict[str, Any]] = []

    safety_checks = (
        ("SHADOW_ONLY_REQUIRED", bool(policy.get("shadow_only", False))),
        (
            "BROKER_WRITE_MUST_BE_DISABLED",
            not bool(policy.get("broker_write_enabled", True)),
        ),
        (
            "LIVE_TRADING_MUST_BE_DISABLED",
            not bool(policy.get("live_trading_enabled", True)),
        ),
        (
            "WINDOWS_TASK_INSTALL_MUST_BE_DISABLED",
            not bool(policy.get("windows_task_install_enabled", True)),
        ),
    )
    for code, passed in safety_checks:
        if not passed:
            issues.append({
                "code": code,
                "blocking": True,
                "detail": "scheduler safety policy failed",
            })

    interval_minutes = int(policy.get("interval_minutes", 15))
    heartbeat_timeout_minutes = int(
        policy.get("heartbeat_timeout_minutes", 30)
    )
    maximum_lateness_minutes = int(
        policy.get("maximum_lateness_minutes", 10)
    )

    if interval_minutes < 1:
        issues.append({
            "code": "INVALID_INTERVAL",
            "blocking": True,
            "detail": str(interval_minutes),
        })

    cycle_foundation_ready = cycle_result.get("state") in {
        "AUTONOMOUS_SHADOW_CYCLE_READY",
        "AUTONOMOUS_SHADOW_CYCLE_COMPLETE",
    }

    duplicate_scheduler = bool(scheduler_lock.get("active", False))
    if authorize_next_cycle and duplicate_scheduler:
        issues.append({
            "code": "DUPLICATE_SCHEDULER_BLOCKED",
            "blocking": True,
            "detail": str(scheduler_lock.get("scheduler_id", "")),
        })

    heartbeat_written = False
    if write_heartbeat:
        heartbeat = {
            "stage": "V82.06",
            "last_heartbeat_at": observed_iso,
            "scheduler_active": True,
            "shadow_only": True,
        }
        write_json(heartbeat_path, heartbeat)
        heartbeat_written = True

    heartbeat_age_seconds: float | None = None
    heartbeat_timeout = False
    if heartbeat.get("last_heartbeat_at"):
        heartbeat_time = parse_iso(str(heartbeat["last_heartbeat_at"]))
        heartbeat_age_seconds = max(
            0.0,
            (observed - heartbeat_time).total_seconds(),
        )
        heartbeat_timeout = (
            heartbeat_age_seconds
            > heartbeat_timeout_minutes * 60
        )

    last_cycle_at = cycle_result.get("observed_at")
    if last_cycle_at:
        last_cycle_time = parse_iso(str(last_cycle_at))
    else:
        last_cycle_time = observed

    next_cycle_time = last_cycle_time + timedelta(
        minutes=interval_minutes
    )
    cycle_due = observed >= next_cycle_time
    lateness_seconds = max(
        0.0,
        (observed - next_cycle_time).total_seconds(),
    )
    cycle_late = (
        cycle_due
        and lateness_seconds > maximum_lateness_minutes * 60
    )

    blocking = any(item.get("blocking") for item in issues)
    next_cycle_authorized = False
    scheduler_lock_written = False
    scheduler_event_written = False

    if blocking:
        state, status = "SHADOW_SCHEDULER_SAFE_MODE", "BLOCKED"
    elif heartbeat_timeout:
        state, status = "SHADOW_SCHEDULER_HEARTBEAT_TIMEOUT", "PASS"
    elif not cycle_foundation_ready:
        state, status = "WAIT_AUTONOMOUS_SHADOW_CYCLE", "PASS"
    elif cycle_late:
        state, status = "SHADOW_SCHEDULER_CYCLE_LATE", "PASS"
    elif not cycle_due:
        state, status = "SHADOW_SCHEDULER_WAIT_INTERVAL", "PASS"
    elif authorize_next_cycle:
        scheduler_id = (
            "shadow-scheduler-"
            + observed.strftime("%Y%m%dT%H%M%S")
        )
        write_json(scheduler_lock_path, {
            "active": True,
            "scheduler_id": scheduler_id,
            "authorized_at": observed_iso,
            "next_cycle_at": next_cycle_time.isoformat(),
            "shadow_only": True,
        })
        scheduler_lock_written = True
        next_cycle_authorized = True
        append_jsonl(scheduler_ledger_path, {
            "stage": "V82.07",
            "event": "NEXT_CYCLE_AUTHORIZED",
            "scheduler_id": scheduler_id,
            "authorized_at": observed_iso,
            "scheduled_for": next_cycle_time.isoformat(),
            "lateness_seconds": round(lateness_seconds, 3),
            "shadow_only": True,
        })
        scheduler_event_written = True
        state, status = "SHADOW_SCHEDULER_CYCLE_AUTHORIZED", "PASS"
    else:
        state, status = "SHADOW_SCHEDULER_CYCLE_DUE", "PASS"

    dashboard = {
        "stage": "V82.08",
        "scheduler_state": state,
        "cycle_foundation_ready": cycle_foundation_ready,
        "interval_minutes": interval_minutes,
        "heartbeat_age_seconds": (
            round(heartbeat_age_seconds, 3)
            if heartbeat_age_seconds is not None else None
        ),
        "heartbeat_timeout": heartbeat_timeout,
        "cycle_due": cycle_due,
        "cycle_late": cycle_late,
        "next_cycle_at": next_cycle_time.isoformat(),
        "next_cycle_authorized": next_cycle_authorized,
        "read_only": True,
        "broker_write_enabled": False,
        "live_trading_enabled": False,
        "observed_at": observed_iso,
    }
    write_json(dashboard_path, dashboard)

    result = {
        "stage_range": "V82.05-V82.08",
        "implementation_type": "AUTONOMOUS_SHADOW_SCHEDULER",
        "status": status,
        "state": state,
        "cycle_foundation_ready": cycle_foundation_ready,
        "interval_minutes": interval_minutes,
        "heartbeat_timeout_minutes": heartbeat_timeout_minutes,
        "maximum_lateness_minutes": maximum_lateness_minutes,
        "heartbeat_requested": write_heartbeat,
        "heartbeat_written": heartbeat_written,
        "heartbeat_age_seconds": (
            round(heartbeat_age_seconds, 3)
            if heartbeat_age_seconds is not None else None
        ),
        "heartbeat_timeout": heartbeat_timeout,
        "cycle_due": cycle_due,
        "cycle_late": cycle_late,
        "lateness_seconds": round(lateness_seconds, 3),
        "next_cycle_at": next_cycle_time.isoformat(),
        "authorize_next_cycle_requested": authorize_next_cycle,
        "next_cycle_authorized": next_cycle_authorized,
        "duplicate_scheduler": duplicate_scheduler,
        "scheduler_lock_written": scheduler_lock_written,
        "scheduler_event_written": scheduler_event_written,
        "dashboard_state_written": True,
        "continuous_loop_enabled": False,
        "windows_task_install_enabled": False,
        "shadow_only": True,
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
            "V82_09_SHADOW_PERFORMANCE_ANALYTICS"
            if state in {
                "SHADOW_SCHEDULER_WAIT_INTERVAL",
                "SHADOW_SCHEDULER_CYCLE_DUE",
                "SHADOW_SCHEDULER_CYCLE_AUTHORIZED",
            }
            else "V82_05_TO_V82_08_WAIT_OR_RECOVER"
        ),
        "validation_mode": "LOCAL_SHADOW_SCHEDULER_ONLY",
        "observed_at": observed_iso,
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
