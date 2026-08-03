
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
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


def calculate_drawdown(equity_values: list[float]) -> dict[str, float]:
    if not equity_values:
        return {
            "maximum_drawdown": 0.0,
            "maximum_drawdown_pct": 0.0,
        }

    peak = equity_values[0]
    max_drawdown = 0.0
    max_drawdown_pct = 0.0

    for equity in equity_values:
        peak = max(peak, equity)
        drawdown = peak - equity
        drawdown_pct = (drawdown / peak * 100.0) if peak > 0 else 0.0
        max_drawdown = max(max_drawdown, drawdown)
        max_drawdown_pct = max(max_drawdown_pct, drawdown_pct)

    return {
        "maximum_drawdown": round(max_drawdown, 8),
        "maximum_drawdown_pct": round(max_drawdown_pct, 8),
    }


def calculate_trade_metrics(trade_pnls: list[float]) -> dict[str, float | int]:
    wins = [value for value in trade_pnls if value > 0]
    losses = [value for value in trade_pnls if value < 0]
    breakeven = [value for value in trade_pnls if value == 0]

    trade_count = len(trade_pnls)
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    average_win = sum(wins) / len(wins) if wins else 0.0
    average_loss = abs(sum(losses) / len(losses)) if losses else 0.0
    win_rate_pct = len(wins) / trade_count * 100.0 if trade_count else 0.0
    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else (float("inf") if gross_profit > 0 else 0.0)
    )
    expectancy = (
        sum(trade_pnls) / trade_count
        if trade_count else 0.0
    )

    return {
        "trade_count": trade_count,
        "wins": len(wins),
        "losses": len(losses),
        "breakeven": len(breakeven),
        "gross_profit": round(gross_profit, 8),
        "gross_loss": round(gross_loss, 8),
        "average_win": round(average_win, 8),
        "average_loss": round(average_loss, 8),
        "win_rate_pct": round(win_rate_pct, 8),
        "profit_factor": (
            "INF"
            if math.isinf(profit_factor)
            else round(profit_factor, 8)
        ),
        "expectancy": round(expectancy, 8),
    }


def calculate_cycle_health(cycles: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(cycles)
    completed = sum(
        1 for row in cycles if bool(row.get("completed", False))
    )
    failed = total - completed
    durations = [
        float(row.get("elapsed_ms", 0.0) or 0.0)
        for row in cycles
    ]
    average_elapsed_ms = (
        sum(durations) / len(durations) if durations else 0.0
    )
    success_rate_pct = (
        completed / total * 100.0 if total else 0.0
    )
    return {
        "cycle_count": total,
        "completed_cycles": completed,
        "failed_cycles": failed,
        "cycle_success_rate_pct": round(success_rate_pct, 8),
        "average_cycle_elapsed_ms": round(average_elapsed_ms, 8),
    }


def run_shadow_performance_analytics(
    *,
    equity_history_path: Path,
    portfolio_state_path: Path,
    cycle_ledger_path: Path,
    policy_path: Path,
    analytics_path: Path,
    health_report_path: Path,
    dashboard_path: Path,
    result_path: Path,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []

    try:
        equity_history = load_jsonl(equity_history_path)
    except Exception as exc:
        equity_history = []
        issues.append({
            "code": "INVALID_EQUITY_HISTORY",
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
        cycles = load_jsonl(cycle_ledger_path)
    except Exception as exc:
        cycles = []
        issues.append({
            "code": "INVALID_CYCLE_LEDGER",
            "blocking": True,
            "detail": str(exc),
        })

    try:
        policy = load_json(policy_path)
    except Exception as exc:
        policy = {}
        issues.append({
            "code": "INVALID_ANALYTICS_POLICY",
            "blocking": True,
            "detail": str(exc),
        })

    if not policy:
        issues.append({
            "code": "ANALYTICS_POLICY_NOT_FOUND",
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
    )
    for code, passed in safety_checks:
        if not passed:
            issues.append({
                "code": code,
                "blocking": True,
                "detail": "analytics safety policy failed",
            })

    equity_values = [
        float(row.get("equity", 0.0) or 0.0)
        for row in equity_history
        if isinstance(row.get("equity"), (int, float))
    ]

    initial_equity = (
        equity_values[0]
        if equity_values
        else float(policy.get("initial_equity", 100000.0))
    )
    latest_equity = (
        equity_values[-1]
        if equity_values
        else float(portfolio.get("equity", initial_equity) or initial_equity)
    )
    cumulative_pnl = latest_equity - initial_equity
    cumulative_return_pct = (
        cumulative_pnl / initial_equity * 100.0
        if initial_equity > 0 else 0.0
    )

    trade_pnls = [
        float(value)
        for value in policy.get("trade_pnls", [])
        if isinstance(value, (int, float))
    ]
    if not trade_pnls:
        realized = float(portfolio.get("realized_pnl", 0.0) or 0.0)
        if realized != 0:
            trade_pnls = [realized]

    trade_metrics = calculate_trade_metrics(trade_pnls)
    drawdown = calculate_drawdown(
        equity_values if equity_values else [initial_equity, latest_equity]
    )
    cycle_health = calculate_cycle_health(cycles)

    maximum_drawdown = float(drawdown["maximum_drawdown"])
    recovery_factor = (
        cumulative_pnl / maximum_drawdown
        if maximum_drawdown > 0 else 0.0
    )

    minimum_samples = int(policy.get("minimum_equity_samples", 5))
    minimum_cycles = int(policy.get("minimum_cycles", 3))
    minimum_cycle_success_rate_pct = float(
        policy.get("minimum_cycle_success_rate_pct", 90.0)
    )

    analytics_complete = (
        len(equity_values) >= minimum_samples
        and cycle_health["cycle_count"] >= minimum_cycles
    )

    health_reasons: list[str] = []
    if len(equity_values) < minimum_samples:
        health_reasons.append("MINIMUM_EQUITY_SAMPLES_NOT_MET")
    if cycle_health["cycle_count"] < minimum_cycles:
        health_reasons.append("MINIMUM_CYCLES_NOT_MET")
    if (
        cycle_health["cycle_count"] > 0
        and cycle_health["cycle_success_rate_pct"]
        < minimum_cycle_success_rate_pct
    ):
        health_reasons.append("CYCLE_SUCCESS_RATE_BELOW_THRESHOLD")

    blocking = any(item.get("blocking") for item in issues)
    if blocking:
        state, status = "SHADOW_ANALYTICS_SAFE_MODE", "BLOCKED"
    elif analytics_complete and not health_reasons:
        state, status = "SHADOW_ANALYTICS_COMPLETE", "PASS"
    else:
        state, status = "SHADOW_ANALYTICS_IN_PROGRESS", "PASS"

    now = datetime.now(timezone.utc).isoformat()

    analytics = {
        "stage": "V82.09-V82.11",
        "initial_equity": round(initial_equity, 8),
        "latest_equity": round(latest_equity, 8),
        "cumulative_pnl": round(cumulative_pnl, 8),
        "cumulative_return_pct": round(cumulative_return_pct, 8),
        **trade_metrics,
        **drawdown,
        "recovery_factor": round(recovery_factor, 8),
        **cycle_health,
        "equity_sample_count": len(equity_values),
        "analytics_complete": analytics_complete,
        "health_reasons": health_reasons,
        "observed_at": now,
    }
    write_json(analytics_path, analytics)

    health_report = {
        "stage": "V82.12",
        "state": state,
        "analytics_complete": analytics_complete,
        "cycle_success_rate_pct": cycle_health[
            "cycle_success_rate_pct"
        ],
        "maximum_drawdown_pct": drawdown[
            "maximum_drawdown_pct"
        ],
        "cumulative_return_pct": round(cumulative_return_pct, 8),
        "profit_factor": trade_metrics["profit_factor"],
        "expectancy": trade_metrics["expectancy"],
        "recovery_factor": round(recovery_factor, 8),
        "health_reasons": health_reasons,
        "observed_at": now,
    }
    write_json(health_report_path, health_report)

    dashboard = {
        "stage": "V82.12",
        "analytics_state": state,
        "analytics_complete": analytics_complete,
        "equity_sample_count": len(equity_values),
        "trade_count": trade_metrics["trade_count"],
        "win_rate_pct": trade_metrics["win_rate_pct"],
        "profit_factor": trade_metrics["profit_factor"],
        "expectancy": trade_metrics["expectancy"],
        "maximum_drawdown_pct": drawdown["maximum_drawdown_pct"],
        "recovery_factor": round(recovery_factor, 8),
        "cycle_count": cycle_health["cycle_count"],
        "cycle_success_rate_pct": cycle_health[
            "cycle_success_rate_pct"
        ],
        "health_reasons": health_reasons,
        "read_only": True,
        "broker_write_enabled": False,
        "live_trading_enabled": False,
        "observed_at": now,
    }
    write_json(dashboard_path, dashboard)

    result = {
        "stage_range": "V82.09-V82.12",
        "implementation_type": "SHADOW_PERFORMANCE_ANALYTICS",
        "status": status,
        "state": state,
        "analytics_complete": analytics_complete,
        "equity_sample_count": len(equity_values),
        "initial_equity": round(initial_equity, 8),
        "latest_equity": round(latest_equity, 8),
        "cumulative_pnl": round(cumulative_pnl, 8),
        "cumulative_return_pct": round(cumulative_return_pct, 8),
        **trade_metrics,
        **drawdown,
        "recovery_factor": round(recovery_factor, 8),
        **cycle_health,
        "health_reasons": health_reasons,
        "analytics_written": True,
        "health_report_written": True,
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
            "V82_13_SHADOW_RISK_CONTROLLER"
            if analytics_complete
            else "V82_09_TO_V82_12_CONTINUE_ANALYTICS"
        ),
        "validation_mode": "LOCAL_SHADOW_ANALYTICS_ONLY",
        "observed_at": now,
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
