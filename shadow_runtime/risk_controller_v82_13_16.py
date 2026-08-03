
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


def evaluate_risk(
    *,
    analytics: dict[str, Any],
    portfolio: dict[str, Any],
    policy: dict[str, Any],
    emergency_stop_requested: bool = False,
    recovery_requested: bool = False,
) -> dict[str, Any]:
    reasons: list[str] = []

    daily_loss = float(
        policy.get("daily_realized_pnl_override", analytics.get("cumulative_pnl", 0.0))
        or 0.0
    )
    drawdown_pct = float(
        analytics.get("maximum_drawdown_pct", 0.0) or 0.0
    )
    gross_exposure_pct = float(
        portfolio.get("gross_exposure_pct", 0.0) or 0.0
    )
    symbol_exposures = portfolio.get("symbol_exposures_pct", {})
    if not isinstance(symbol_exposures, dict):
        symbol_exposures = {}
    trade_count = int(
        policy.get("daily_trade_count_override", analytics.get("trade_count", 0))
        or 0
    )
    consecutive_losses = int(
        policy.get("consecutive_losses_override", 0) or 0
    )

    max_daily_loss = abs(float(policy.get("maximum_daily_loss", 500.0)))
    max_drawdown_pct = float(policy.get("maximum_drawdown_pct", 5.0))
    max_gross_exposure_pct = float(
        policy.get("maximum_gross_exposure_pct", 100.0)
    )
    max_symbol_exposure_pct = float(
        policy.get("maximum_symbol_exposure_pct", 35.0)
    )
    max_daily_trades = int(policy.get("maximum_daily_trades", 10))
    max_consecutive_losses = int(
        policy.get("maximum_consecutive_losses", 3)
    )

    if daily_loss <= -max_daily_loss:
        reasons.append("MAXIMUM_DAILY_LOSS_EXCEEDED")
    if drawdown_pct >= max_drawdown_pct:
        reasons.append("MAXIMUM_DRAWDOWN_EXCEEDED")
    if gross_exposure_pct >= max_gross_exposure_pct:
        reasons.append("MAXIMUM_GROSS_EXPOSURE_EXCEEDED")
    if any(
        float(value or 0.0) >= max_symbol_exposure_pct
        for value in symbol_exposures.values()
    ):
        reasons.append("MAXIMUM_SYMBOL_EXPOSURE_EXCEEDED")
    if trade_count >= max_daily_trades:
        reasons.append("MAXIMUM_DAILY_TRADES_EXCEEDED")
    if consecutive_losses >= max_consecutive_losses:
        reasons.append("MAXIMUM_CONSECUTIVE_LOSSES_EXCEEDED")
    if emergency_stop_requested:
        reasons.append("MANUAL_EMERGENCY_STOP_REQUESTED")

    emergency_stop_required = bool(reasons)
    recovery_allowed = (
        recovery_requested
        and not emergency_stop_requested
        and not any(
            reason != "MANUAL_EMERGENCY_STOP_REQUESTED"
            for reason in reasons
        )
    )

    return {
        "daily_loss": round(daily_loss, 8),
        "drawdown_pct": round(drawdown_pct, 8),
        "gross_exposure_pct": round(gross_exposure_pct, 8),
        "symbol_exposures_pct": symbol_exposures,
        "trade_count": trade_count,
        "consecutive_losses": consecutive_losses,
        "risk_reasons": reasons,
        "emergency_stop_required": emergency_stop_required,
        "recovery_allowed": recovery_allowed,
    }


def run_shadow_risk_controller(
    *,
    analytics_result_path: Path,
    portfolio_state_path: Path,
    policy_path: Path,
    kill_switch_path: Path,
    recovery_lock_path: Path,
    risk_report_path: Path,
    dashboard_path: Path,
    result_path: Path,
    emergency_stop_requested: bool = False,
    recovery_requested: bool = False,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []

    try:
        analytics = load_json(analytics_result_path)
    except Exception as exc:
        analytics = {}
        issues.append({
            "code": "INVALID_ANALYTICS_RESULT",
            "blocking": True,
            "detail": str(exc),
        })

    try:
        portfolio = load_json(portfolio_state_path)
    except Exception as exc:
        portfolio = {}
        issues.append({
            "code": "INVALID_PORTFOLIO_STATE",
            "blocking": True,
            "detail": str(exc),
        })

    try:
        policy = load_json(policy_path)
    except Exception as exc:
        policy = {}
        issues.append({
            "code": "INVALID_RISK_POLICY",
            "blocking": True,
            "detail": str(exc),
        })

    if not policy:
        issues.append({
            "code": "RISK_POLICY_NOT_FOUND",
            "blocking": True,
            "detail": str(policy_path),
        })

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
            "ORDER_SUBMISSION_MUST_BE_DISABLED",
            not bool(policy.get("order_submission_enabled", True)),
        ),
    )
    for code, passed in safety_checks:
        if not passed:
            issues.append({
                "code": code,
                "blocking": True,
                "detail": "risk safety policy failed",
            })

    metrics = evaluate_risk(
        analytics=analytics,
        portfolio=portfolio,
        policy=policy,
        emergency_stop_requested=emergency_stop_requested,
        recovery_requested=recovery_requested,
    )

    existing_kill_switch = load_json(kill_switch_path)
    kill_switch_active = bool(existing_kill_switch.get("active", False))
    now = datetime.now(timezone.utc).isoformat()

    if metrics["emergency_stop_required"]:
        kill_switch_active = True

    if recovery_requested:
        if metrics["recovery_allowed"]:
            kill_switch_active = False
        elif kill_switch_active:
            issues.append({
                "code": "RECOVERY_NOT_ALLOWED",
                "blocking": True,
                "detail": "risk conditions or manual stop still active",
            })

    blocking = any(item.get("blocking") for item in issues)

    if blocking:
        state, status = "SHADOW_RISK_CONTROLLER_SAFE_MODE", "BLOCKED"
    elif kill_switch_active:
        state, status = "SHADOW_RISK_KILL_SWITCH_ACTIVE", "PASS"
    else:
        state, status = "SHADOW_RISK_CLEAR", "PASS"

    write_json(kill_switch_path, {
        "stage": "V82.15",
        "active": kill_switch_active,
        "risk_reasons": metrics["risk_reasons"],
        "emergency_stop_requested": emergency_stop_requested,
        "updated_at": now,
        "shadow_only": True,
    })

    recovery_lock_active = kill_switch_active or blocking
    write_json(recovery_lock_path, {
        "stage": "V82.15",
        "active": recovery_lock_active,
        "recovery_requested": recovery_requested,
        "recovery_allowed": metrics["recovery_allowed"],
        "updated_at": now,
        "shadow_only": True,
    })

    risk_report = {
        "stage": "V82.13-V82.15",
        "state": state,
        **metrics,
        "kill_switch_active": kill_switch_active,
        "recovery_lock_active": recovery_lock_active,
        "observed_at": now,
    }
    write_json(risk_report_path, risk_report)

    dashboard = {
        "stage": "V82.16",
        "risk_state": state,
        "kill_switch_active": kill_switch_active,
        "recovery_lock_active": recovery_lock_active,
        "daily_loss": metrics["daily_loss"],
        "drawdown_pct": metrics["drawdown_pct"],
        "gross_exposure_pct": metrics["gross_exposure_pct"],
        "trade_count": metrics["trade_count"],
        "consecutive_losses": metrics["consecutive_losses"],
        "risk_reasons": metrics["risk_reasons"],
        "read_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "observed_at": now,
    }
    write_json(dashboard_path, dashboard)

    result = {
        "stage_range": "V82.13-V82.16",
        "implementation_type": "SHADOW_RISK_CONTROLLER",
        "status": status,
        "state": state,
        **metrics,
        "kill_switch_active": kill_switch_active,
        "recovery_lock_active": recovery_lock_active,
        "kill_switch_written": True,
        "recovery_lock_written": True,
        "risk_report_written": True,
        "dashboard_state_written": True,
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
            "V82_17_SHADOW_TRADE_AUTHORIZATION"
            if state == "SHADOW_RISK_CLEAR"
            else "V82_13_TO_V82_16_WAIT_OR_RECOVER"
        ),
        "validation_mode": "LOCAL_SHADOW_RISK_CONTROLLER_ONLY",
        "observed_at": now,
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
