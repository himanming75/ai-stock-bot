from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


REQUIRED_SAFETY_FALSE = (
    "broker_write_enabled",
    "order_submission_enabled",
    "live_trading_enabled",
    "external_network_enabled",
    "continuous_loop_enabled",
    "windows_task_enabled",
    "automatic_broker_execution_enabled",
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


def validation_id(validation_date: str) -> str:
    digest = hashlib.sha256(
        f"multi-day-paper-validation|{validation_date}".encode("utf-8")
    ).hexdigest()[:20]
    return f"paper-day-{digest}"


def normalize_observed_at(value: str) -> datetime:
    observed = datetime.fromisoformat(value) if value else datetime.now(timezone.utc)
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    return observed


def run_multi_day_paper_validation(
    *,
    autonomous_result_path: Path,
    policy_path: Path,
    daily_ledger_path: Path,
    summary_path: Path,
    dashboard_path: Path,
    result_path: Path,
    observed_at_override: str = "",
    validation_date_override: str = "",
    minimum_days: int = 3,
    reset_ledger: bool = False,
) -> dict[str, Any]:
    observed = normalize_observed_at(observed_at_override)
    observed_iso = observed.isoformat()
    validation_date = validation_date_override or observed.date().isoformat()
    date.fromisoformat(validation_date)

    if minimum_days < 2:
        raise ValueError("minimum_days must be at least 2")

    if reset_ledger and daily_ledger_path.exists():
        daily_ledger_path.unlink()

    issues: list[dict[str, Any]] = []
    try:
        autonomous = load_json(autonomous_result_path)
    except Exception as exc:
        autonomous = {}
        issues.append({
            "code": "INVALID_AUTONOMOUS_RESULT",
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

    if not autonomous:
        issues.append({
            "code": "AUTONOMOUS_RESULT_NOT_FOUND",
            "blocking": True,
            "detail": str(autonomous_result_path),
        })

    accepted_states = {
        "PAPER_AUTONOMOUS_CYCLE_READY",
        "PAPER_AUTONOMOUS_CYCLE_AUTHORIZED",
        "PAPER_AUTONOMOUS_CYCLE_ACTIVE",
        "PAPER_AUTONOMOUS_CYCLE_COMPLETED",
        "PAPER_AUTONOMOUS_LOCK_CLEARED",
    }
    autonomous_state = str(autonomous.get("state", ""))
    if autonomous_state not in accepted_states:
        issues.append({
            "code": "AUTONOMOUS_STATE_NOT_ELIGIBLE",
            "blocking": True,
            "detail": autonomous_state,
        })

    if autonomous.get("status") != "PASS":
        issues.append({
            "code": "AUTONOMOUS_STATUS_NOT_PASS",
            "blocking": True,
            "detail": str(autonomous.get("status", "")),
        })

    if not policy:
        issues.append({
            "code": "MULTI_DAY_POLICY_NOT_FOUND",
            "blocking": True,
            "detail": str(policy_path),
        })

    if not bool(policy.get("paper_only", False)):
        issues.append({
            "code": "PAPER_ONLY_REQUIRED",
            "blocking": True,
            "detail": "paper_only must be true",
        })

    for key in REQUIRED_SAFETY_FALSE:
        if bool(policy.get(key, True)):
            issues.append({
                "code": f"{key.upper()}_MUST_BE_DISABLED",
                "blocking": True,
                "detail": key,
            })

    try:
        existing = load_jsonl(daily_ledger_path)
    except Exception as exc:
        existing = []
        issues.append({
            "code": "INVALID_DAILY_LEDGER",
            "blocking": True,
            "detail": str(exc),
        })

    duplicate_date = any(
        row.get("validation_date") == validation_date for row in existing
    )
    blocking = any(item.get("blocking") for item in issues)
    daily_record_written = False

    if duplicate_date:
        issues.append({
            "code": "DUPLICATE_VALIDATION_DATE",
            "blocking": False,
            "detail": validation_date,
        })
    elif not blocking:
        record = {
            "stage": "V83.78",
            "event": "MULTI_DAY_PAPER_VALIDATION_DAY_RECORDED",
            "validation_id": validation_id(validation_date),
            "validation_date": validation_date,
            "observed_at": observed_iso,
            "source_stage_range": autonomous.get("stage_range", ""),
            "source_state": autonomous_state,
            "source_status": autonomous.get("status", ""),
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
            "actual_paper_orders_submitted": 0,
            "live_orders_submitted": 0,
            "network_requests_executed": 0,
            "write_requests_executed": 0,
        }
        append_jsonl(daily_ledger_path, record)
        existing.append(record)
        daily_record_written = True

    unique_dates = sorted({
        str(row.get("validation_date"))
        for row in existing
        if row.get("validation_date")
    })
    completed_days = len(unique_dates)
    requirement_met = completed_days >= minimum_days and not blocking

    if blocking:
        state = "MULTI_DAY_PAPER_VALIDATION_BLOCKED"
        status = "BLOCKED"
    elif requirement_met:
        state = "MULTI_DAY_PAPER_VALIDATION_COMPLETE"
        status = "PASS"
    else:
        state = "MULTI_DAY_PAPER_VALIDATION_IN_PROGRESS"
        status = "PASS"

    summary = {
        "stage": "V83.79",
        "state": state,
        "status": status,
        "minimum_days": minimum_days,
        "completed_days": completed_days,
        "remaining_days": max(0, minimum_days - completed_days),
        "validation_dates": unique_dates,
        "requirement_met": requirement_met,
        "paper_only": True,
        "continuous_loop_enabled": False,
        "windows_task_enabled": False,
        "automatic_broker_execution_enabled": False,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
        "actual_paper_orders_submitted": 0,
        "live_orders_submitted": 0,
        "observed_at": observed_iso,
    }
    write_json(summary_path, summary)

    dashboard = {
        **summary,
        "stage": "V83.80",
        "multi_day_paper_validation_state": state,
        "daily_record_written": daily_record_written,
        "duplicate_date": duplicate_date,
        "latest_validation_date": validation_date,
    }
    write_json(dashboard_path, dashboard)

    result = {
        **dashboard,
        "stage_range": "V83.77-V83.80",
        "implementation_type": "MULTI_DAY_PAPER_VALIDATION",
        "validation_mode": "LOCAL_MANUAL_DATE_ADVANCEMENT",
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "broker_command_execution_enabled": False,
        "issue_count": len(issues),
        "blocking_issue_count": sum(
            1 for item in issues if item.get("blocking")
        ),
        "issues": issues,
        "next_phase": (
            "V83_81_PAPER_STABILITY_CERTIFICATION"
            if requirement_met
            else "V83_77_TO_V83_80_CONTINUE_VALIDATION"
            if status == "PASS"
            else "V83_77_TO_V83_80_RECOVER"
        ),
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
