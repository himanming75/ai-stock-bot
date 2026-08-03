
from __future__ import annotations

import json
from datetime import datetime, timezone
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


def evaluate_end_of_day(
    *,
    session: dict[str, Any],
    scheduler: dict[str, Any],
    intraday: dict[str, Any],
    performance: dict[str, Any],
    risk: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    reasons: list[str] = []

    session_active = bool(session.get("session_active", False))
    session_state = str(session.get("state", ""))
    market_closed = bool(session.get("market_closed", False))
    scheduler_active_tick = bool(scheduler.get("active_tick", False))
    loop_active = bool(intraday.get("active_loop", False))
    loop_state = str(intraday.get("state", ""))
    risk_clear = str(risk.get("state", "")) == "SHADOW_RISK_CLEAR"

    if not market_closed:
        reasons.append("MARKET_NOT_CLOSED")
    if scheduler_active_tick:
        reasons.append("ACTIVE_SCHEDULER_TICK_EXISTS")
    if loop_active:
        reasons.append("ACTIVE_INTRADAY_LOOP_EXISTS")
    if loop_state == "INTRADAY_LOOP_RECOVERY_REQUIRED":
        reasons.append("INTRADAY_LOOP_RECOVERY_REQUIRED")
    if not risk_clear:
        reasons.append("RISK_NOT_CLEAR")

    allow_inactive_session = bool(
        policy.get("allow_inactive_session_certification", True)
    )
    if not session_active and not allow_inactive_session:
        reasons.append("SESSION_NOT_ACTIVE")

    eod_ready = len(reasons) == 0
    return {
        "session_active": session_active,
        "session_state": session_state,
        "market_closed": market_closed,
        "scheduler_active_tick": scheduler_active_tick,
        "intraday_loop_active": loop_active,
        "intraday_loop_state": loop_state,
        "risk_clear": risk_clear,
        "eod_ready": eod_ready,
        "eod_reasons": reasons,
        "cumulative_pnl": float(
            performance.get("cumulative_pnl", 0.0) or 0.0
        ),
        "cumulative_return_pct": float(
            performance.get("cumulative_return_pct", 0.0) or 0.0
        ),
        "trade_count": int(
            performance.get("trade_count", 0) or 0
        ),
        "maximum_drawdown_pct": float(
            performance.get("maximum_drawdown_pct", 0.0) or 0.0
        ),
    }


def run_end_of_day_manager(
    *,
    session_result_path: Path,
    scheduler_result_path: Path,
    intraday_result_path: Path,
    performance_result_path: Path,
    risk_result_path: Path,
    policy_path: Path,
    daily_report_path: Path,
    certification_path: Path,
    ledger_path: Path,
    next_day_state_path: Path,
    dashboard_path: Path,
    result_path: Path,
    certify_day_requested: bool = False,
    prepare_next_day_requested: bool = False,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    issues: list[dict[str, Any]] = []

    paths = {
        "session": session_result_path,
        "scheduler": scheduler_result_path,
        "intraday": intraday_result_path,
        "performance": performance_result_path,
        "risk": risk_result_path,
        "policy": policy_path,
    }
    inputs: dict[str, dict[str, Any]] = {}
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
            "code": "END_OF_DAY_POLICY_NOT_FOUND",
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
                "detail": "end-of-day safety policy failed",
            })

    evaluation = evaluate_end_of_day(
        session=inputs["session"],
        scheduler=inputs["scheduler"],
        intraday=inputs["intraday"],
        performance=inputs["performance"],
        risk=inputs["risk"],
        policy=policy,
    )

    blocking = any(item.get("blocking") for item in issues)
    report_written = False
    certification_written = False
    ledger_written = False
    next_day_state_written = False
    day_certified = False
    next_day_ready = False

    trading_date = str(
        inputs["session"].get(
            "trading_date",
            inputs["session"].get("observed_at", now_iso)[:10],
        )
    )
    session_id = str(inputs["session"].get("session_id", ""))

    daily_report = {
        "stage": "V82.33-V82.34",
        "trading_date": trading_date,
        "session_id": session_id,
        **evaluation,
        "session_started": bool(
            inputs["session"].get("session_started", False)
        ),
        "session_ended": bool(
            inputs["session"].get("session_ended", False)
        ),
        "scheduler_state": inputs["scheduler"].get("state", ""),
        "intraday_state": inputs["intraday"].get("state", ""),
        "performance_state": inputs["performance"].get("state", ""),
        "risk_state": inputs["risk"].get("state", ""),
        "observed_at": now_iso,
        "paper_only": True,
    }
    write_json(daily_report_path, daily_report)
    report_written = True

    if blocking:
        state, status = "END_OF_DAY_SAFE_MODE", "BLOCKED"
    elif certify_day_requested:
        if evaluation["eod_ready"]:
            certification = {
                "stage": "V82.35",
                "trading_date": trading_date,
                "session_id": session_id,
                "certified": True,
                "certification_state": "DAILY_PAPER_CERTIFIED",
                "eod_reasons": [],
                "cumulative_pnl": evaluation["cumulative_pnl"],
                "trade_count": evaluation["trade_count"],
                "maximum_drawdown_pct": evaluation[
                    "maximum_drawdown_pct"
                ],
                "certified_at": now_iso,
                "paper_only": True,
                "broker_write_enabled": False,
                "order_submission_enabled": False,
            }
            write_json(certification_path, certification)
            append_jsonl(ledger_path, {
                **certification,
                "event": "DAILY_CERTIFICATION_WRITTEN",
            })
            certification_written = True
            ledger_written = True
            day_certified = True
            state, status = "DAILY_PAPER_CERTIFIED", "PASS"
        else:
            certification = {
                "stage": "V82.35",
                "trading_date": trading_date,
                "session_id": session_id,
                "certified": False,
                "certification_state": "DAILY_CERTIFICATION_WAIT_GATES",
                "eod_reasons": evaluation["eod_reasons"],
                "observed_at": now_iso,
                "paper_only": True,
            }
            write_json(certification_path, certification)
            certification_written = True
            state, status = "DAILY_CERTIFICATION_WAIT_GATES", "PASS"
    elif prepare_next_day_requested:
        certification = load_json(certification_path)
        day_certified = bool(certification.get("certified", False))
        if day_certified:
            next_day_state = {
                "stage": "V82.36",
                "previous_trading_date": trading_date,
                "previous_session_id": session_id,
                "next_day_ready": True,
                "session_reset_required": True,
                "scheduler_reset_required": True,
                "intraday_loop_reset_required": True,
                "prepared_at": now_iso,
                "paper_only": True,
            }
            write_json(next_day_state_path, next_day_state)
            append_jsonl(ledger_path, {
                **next_day_state,
                "event": "NEXT_TRADING_DAY_PREPARED",
            })
            next_day_state_written = True
            ledger_written = True
            next_day_ready = True
            state, status = "NEXT_TRADING_DAY_READY", "PASS"
        else:
            state, status = "WAIT_DAILY_CERTIFICATION", "PASS"
    else:
        if evaluation["eod_ready"]:
            state, status = "END_OF_DAY_READY_TO_CERTIFY", "PASS"
        else:
            state, status = "END_OF_DAY_WAIT_GATES", "PASS"

    dashboard = {
        "stage": "V82.36",
        "end_of_day_state": state,
        "trading_date": trading_date,
        "session_id": session_id,
        "eod_ready": evaluation["eod_ready"],
        "eod_reasons": evaluation["eod_reasons"],
        "day_certified": day_certified,
        "next_day_ready": next_day_ready,
        "cumulative_pnl": evaluation["cumulative_pnl"],
        "trade_count": evaluation["trade_count"],
        "maximum_drawdown_pct": evaluation["maximum_drawdown_pct"],
        "paper_only": True,
        "read_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "observed_at": now_iso,
    }
    write_json(dashboard_path, dashboard)

    result = {
        "stage_range": "V82.33-V82.36",
        "implementation_type": "END_OF_DAY_MANAGER_AND_DAILY_CERTIFICATION",
        "status": status,
        "state": state,
        "trading_date": trading_date,
        "session_id": session_id,
        **evaluation,
        "certify_day_requested": certify_day_requested,
        "prepare_next_day_requested": prepare_next_day_requested,
        "day_certified": day_certified,
        "next_day_ready": next_day_ready,
        "daily_report_written": report_written,
        "daily_certification_written": certification_written,
        "daily_ledger_written": ledger_written,
        "next_day_state_written": next_day_state_written,
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
            "V82_37_MULTI_DAY_RUNTIME"
            if state in {
                "DAILY_PAPER_CERTIFIED",
                "NEXT_TRADING_DAY_READY",
            }
            else "V82_33_TO_V82_36_WAIT_OR_CERTIFY"
        ),
        "validation_mode": "LOCAL_END_OF_DAY_CERTIFICATION_ONLY",
        "observed_at": now_iso,
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
