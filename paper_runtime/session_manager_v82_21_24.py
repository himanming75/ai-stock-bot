
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


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


def session_id(trading_date: str, started_at: str) -> str:
    raw = f"{trading_date}|{started_at}".encode("utf-8")
    return "paper-session-" + hashlib.sha256(raw).hexdigest()[:20]


def parse_hhmm(value: str) -> time:
    hour_text, minute_text = value.split(":", 1)
    return time(hour=int(hour_text), minute=int(minute_text))


def evaluate_market_day(
    *,
    observed_at: datetime,
    policy: dict[str, Any],
) -> dict[str, Any]:
    timezone_name = str(
        policy.get("market_timezone", "America/New_York")
    )
    market_tz = ZoneInfo(timezone_name)
    local = observed_at.astimezone(market_tz)
    trading_date = local.date().isoformat()

    holidays = {
        str(item)
        for item in policy.get("market_holidays", [])
    }
    weekend = local.weekday() >= 5
    holiday = trading_date in holidays
    trading_day = not weekend and not holiday

    regular_open = parse_hhmm(
        str(policy.get("regular_market_open", "09:30"))
    )
    regular_close = parse_hhmm(
        str(policy.get("regular_market_close", "16:00"))
    )

    market_open = (
        trading_day
        and regular_open <= local.time().replace(tzinfo=None) < regular_close
    )
    market_closed = not market_open

    return {
        "market_timezone": timezone_name,
        "market_local_time": local.isoformat(),
        "trading_date": trading_date,
        "weekend": weekend,
        "holiday": holiday,
        "trading_day": trading_day,
        "market_open": market_open,
        "market_closed": market_closed,
        "regular_market_open": regular_open.strftime("%H:%M"),
        "regular_market_close": regular_close.strftime("%H:%M"),
    }


def run_paper_session_manager(
    *,
    authorization_result_path: Path,
    policy_path: Path,
    session_state_path: Path,
    session_lock_path: Path,
    daily_ledger_path: Path,
    daily_snapshot_path: Path,
    dashboard_path: Path,
    result_path: Path,
    start_session_requested: bool = False,
    end_session_requested: bool = False,
    recover_session_requested: bool = False,
    observed_at: datetime | None = None,
) -> dict[str, Any]:
    now = observed_at or datetime.now(timezone.utc)
    now_iso = now.isoformat()

    issues: list[dict[str, Any]] = []

    try:
        authorization = load_json(authorization_result_path)
    except Exception as exc:
        authorization = {}
        issues.append({
            "code": "INVALID_AUTHORIZATION_RESULT",
            "blocking": True,
            "detail": str(exc),
        })

    try:
        policy = load_json(policy_path)
    except Exception as exc:
        policy = {}
        issues.append({
            "code": "INVALID_SESSION_POLICY",
            "blocking": True,
            "detail": str(exc),
        })

    if not policy:
        issues.append({
            "code": "SESSION_POLICY_NOT_FOUND",
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
    )
    for code, passed in safety_checks:
        if not passed:
            issues.append({
                "code": code,
                "blocking": True,
                "detail": "session safety policy failed",
            })

    market = evaluate_market_day(
        observed_at=now,
        policy=policy,
    )

    authorization_ready = authorization.get("state") in {
        "SHADOW_TRADE_AUTHORIZED",
        "SHADOW_TRADE_NO_ACTION",
        "SHADOW_TRADE_REJECTED",
    }

    state_file = load_json(session_state_path)
    lock_file = load_json(session_lock_path)

    session_active = bool(state_file.get("session_active", False))
    active_session_id = str(state_file.get("session_id", ""))
    duplicate_start = start_session_requested and session_active
    if duplicate_start:
        issues.append({
            "code": "DUPLICATE_SESSION_START_BLOCKED",
            "blocking": True,
            "detail": active_session_id,
        })

    start_allowed = (
        authorization_ready
        and market["trading_day"]
        and market["market_open"]
        and not session_active
    )

    end_allowed = session_active
    recovery_available = (
        bool(lock_file.get("active", False))
        and not session_active
    )

    session_started = False
    session_ended = False
    session_recovered = False
    ledger_written = False
    snapshot_written = False
    current_session_id = active_session_id

    blocking = any(item.get("blocking") for item in issues)

    if blocking:
        state, status = "PAPER_SESSION_MANAGER_SAFE_MODE", "BLOCKED"

    elif recover_session_requested:
        if recovery_available:
            current_session_id = str(lock_file.get("session_id", ""))
            recovered_state = {
                "stage": "V82.23",
                "session_id": current_session_id,
                "session_active": True,
                "trading_date": str(lock_file.get("trading_date", "")),
                "started_at": str(lock_file.get("started_at", "")),
                "recovered_at": now_iso,
                "paper_only": True,
                "broker_write_enabled": False,
                "order_submission_enabled": False,
            }
            write_json(session_state_path, recovered_state)
            session_active = True
            session_recovered = True
            state, status = "PAPER_SESSION_RECOVERED", "PASS"
        else:
            state, status = "PAPER_SESSION_RECOVERY_NOT_AVAILABLE", "PASS"

    elif start_session_requested:
        if start_allowed:
            current_session_id = session_id(
                market["trading_date"],
                now_iso,
            )
            session_payload = {
                "stage": "V82.21",
                "session_id": current_session_id,
                "session_active": True,
                "trading_date": market["trading_date"],
                "started_at": now_iso,
                "start_equity": float(
                    policy.get("starting_equity", 100000.0)
                ),
                "trade_count": 0,
                "paper_only": True,
                "broker_write_enabled": False,
                "order_submission_enabled": False,
            }
            write_json(session_state_path, session_payload)
            write_json(session_lock_path, {
                "stage": "V82.21",
                "active": True,
                "session_id": current_session_id,
                "trading_date": market["trading_date"],
                "started_at": now_iso,
                "paper_only": True,
            })
            append_jsonl(daily_ledger_path, {
                "stage": "V82.22",
                "event": "SESSION_STARTED",
                "session_id": current_session_id,
                "trading_date": market["trading_date"],
                "observed_at": now_iso,
                "paper_only": True,
            })
            ledger_written = True
            session_active = True
            session_started = True
            state, status = "PAPER_SESSION_RUNNING", "PASS"
        elif not authorization_ready:
            state, status = "WAIT_TRADE_AUTHORIZATION", "PASS"
        elif not market["trading_day"]:
            state, status = "PAPER_SESSION_MARKET_HOLIDAY_OR_WEEKEND", "PASS"
        else:
            state, status = "PAPER_SESSION_WAIT_MARKET_OPEN", "PASS"

    elif end_session_requested:
        if end_allowed:
            end_equity = float(
                policy.get(
                    "ending_equity_override",
                    state_file.get(
                        "start_equity",
                        policy.get("starting_equity", 100000.0),
                    ),
                )
            )
            start_equity = float(
                state_file.get(
                    "start_equity",
                    policy.get("starting_equity", 100000.0),
                )
            )
            daily_pnl = end_equity - start_equity
            summary = {
                "stage": "V82.22",
                "session_id": active_session_id,
                "trading_date": str(
                    state_file.get(
                        "trading_date",
                        market["trading_date"],
                    )
                ),
                "started_at": str(state_file.get("started_at", "")),
                "ended_at": now_iso,
                "start_equity": start_equity,
                "end_equity": end_equity,
                "daily_pnl": round(daily_pnl, 8),
                "trade_count": int(
                    state_file.get("trade_count", 0) or 0
                ),
                "session_status": "CLOSED",
                "paper_only": True,
            }
            write_json(daily_snapshot_path, summary)
            snapshot_written = True
            append_jsonl(daily_ledger_path, {
                **summary,
                "event": "SESSION_ENDED",
            })
            ledger_written = True
            write_json(session_state_path, {
                **summary,
                "session_active": False,
            })
            write_json(session_lock_path, {
                "active": False,
                "session_id": active_session_id,
                "ended_at": now_iso,
                "paper_only": True,
            })
            session_active = False
            session_ended = True
            current_session_id = active_session_id
            state, status = "PAPER_SESSION_CLOSED", "PASS"
        else:
            state, status = "PAPER_SESSION_NOT_ACTIVE", "PASS"

    else:
        if session_active:
            state, status = "PAPER_SESSION_RUNNING", "PASS"
        elif not authorization_ready:
            state, status = "WAIT_TRADE_AUTHORIZATION", "PASS"
        elif not market["trading_day"]:
            state, status = "PAPER_SESSION_MARKET_HOLIDAY_OR_WEEKEND", "PASS"
        elif market["market_open"]:
            state, status = "PAPER_SESSION_READY_TO_START", "PASS"
        else:
            state, status = "PAPER_SESSION_WAIT_MARKET_OPEN", "PASS"

    dashboard = {
        "stage": "V82.24",
        "session_state": state,
        "session_id": current_session_id,
        "session_active": session_active,
        "authorization_ready": authorization_ready,
        **market,
        "read_only": True,
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "observed_at": now_iso,
    }
    write_json(dashboard_path, dashboard)

    result = {
        "stage_range": "V82.21-V82.24",
        "implementation_type": "PAPER_TRADING_SESSION_MANAGER",
        "status": status,
        "state": state,
        "session_id": current_session_id,
        "session_active": session_active,
        "session_start_requested": start_session_requested,
        "session_end_requested": end_session_requested,
        "session_recovery_requested": recover_session_requested,
        "session_started": session_started,
        "session_ended": session_ended,
        "session_recovered": session_recovered,
        "duplicate_start": duplicate_start,
        "authorization_ready": authorization_ready,
        "start_allowed": start_allowed,
        "end_allowed": end_allowed,
        "recovery_available": recovery_available,
        **market,
        "daily_ledger_written": ledger_written,
        "daily_snapshot_written": snapshot_written,
        "dashboard_state_written": True,
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
            "V82_25_PAPER_TRADING_SCHEDULER"
            if state in {
                "PAPER_SESSION_RUNNING",
                "PAPER_SESSION_CLOSED",
                "PAPER_SESSION_READY_TO_START",
                "PAPER_SESSION_WAIT_MARKET_OPEN",
                "PAPER_SESSION_MARKET_HOLIDAY_OR_WEEKEND",
            }
            else "V82_21_TO_V82_24_WAIT_OR_RECOVER"
        ),
        "validation_mode": "LOCAL_PAPER_SESSION_MANAGER_ONLY",
        "observed_at": now_iso,
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
