from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def digest_payload(value: dict[str, Any]) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def finite_number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if result != result or result in (float("inf"), float("-inf")):
        return default
    return result


def evaluate_metrics(
    snapshot: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    issues: list[dict[str, Any]] = []
    trades = max(0, int(finite_number(snapshot.get("total_trades"), 0)))
    wins = max(0, int(finite_number(snapshot.get("winning_trades"), 0)))
    losses = max(0, int(finite_number(snapshot.get("losing_trades"), 0)))
    gross_profit = finite_number(snapshot.get("gross_profit"), 0.0)
    gross_loss = abs(finite_number(snapshot.get("gross_loss"), 0.0))
    net_profit = finite_number(snapshot.get("net_profit"), gross_profit - gross_loss)
    max_drawdown_pct = abs(finite_number(snapshot.get("max_drawdown_pct"), 0.0))
    max_daily_loss_pct = abs(finite_number(snapshot.get("max_daily_loss_pct"), 0.0))
    order_rejection_count = max(
        0, int(finite_number(snapshot.get("order_rejection_count"), 0))
    )
    duplicate_order_count = max(
        0, int(finite_number(snapshot.get("duplicate_order_count"), 0))
    )

    if wins + losses > trades:
        issues.append({
            "code": "TRADE_COUNTS_INCONSISTENT",
            "blocking": True,
            "detail": {"trades": trades, "wins": wins, "losses": losses},
        })

    win_rate = (wins / trades * 100.0) if trades else 0.0
    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0
        else (999.0 if gross_profit > 0 else 0.0)
    )

    checks = {
        "minimum_trade_count": trades >= int(policy.get("minimum_trade_count", 1)),
        "net_profit_floor": net_profit >= finite_number(
            policy.get("minimum_net_profit"), 0.0
        ),
        "maximum_drawdown": max_drawdown_pct <= finite_number(
            policy.get("maximum_drawdown_pct"), 100.0
        ),
        "minimum_profit_factor": profit_factor >= finite_number(
            policy.get("minimum_profit_factor"), 0.0
        ),
        "maximum_daily_loss": max_daily_loss_pct <= finite_number(
            policy.get("maximum_daily_loss_pct"), 100.0
        ),
        "order_rejections": order_rejection_count <= int(
            policy.get("maximum_order_rejections", 0)
        ),
        "duplicate_orders_zero": duplicate_order_count == 0,
    }

    metrics = {
        "total_trades": trades,
        "winning_trades": wins,
        "losing_trades": losses,
        "win_rate_pct": round(win_rate, 4),
        "gross_profit": round(gross_profit, 4),
        "gross_loss": round(gross_loss, 4),
        "net_profit": round(net_profit, 4),
        "profit_factor": round(profit_factor, 4),
        "max_drawdown_pct": round(max_drawdown_pct, 4),
        "max_daily_loss_pct": round(max_daily_loss_pct, 4),
        "order_rejection_count": order_rejection_count,
        "duplicate_order_count": duplicate_order_count,
        "checks": checks,
        "checks_passed": sum(1 for passed in checks.values() if passed),
        "checks_total": len(checks),
    }
    metrics["performance_score"] = round(
        metrics["checks_passed"] / metrics["checks_total"] * 100.0,
        2,
    )
    metrics["performance_gate_passed"] = all(checks.values())
    return metrics, issues


def run_performance_production_readiness(
    *,
    stability_result_path: Path,
    performance_snapshot_path: Path,
    policy_path: Path,
    performance_report_path: Path,
    performance_certificate_path: Path,
    risk_gate_path: Path,
    readiness_certificate_path: Path,
    dashboard_path: Path,
    result_path: Path,
    observed_at_override: str = "",
) -> dict[str, Any]:
    observed = (
        datetime.fromisoformat(observed_at_override)
        if observed_at_override
        else datetime.now(timezone.utc)
    )
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    observed_at = observed.isoformat()

    issues: list[dict[str, Any]] = []
    for name, path in (
        ("stability", stability_result_path),
        ("snapshot", performance_snapshot_path),
        ("policy", policy_path),
    ):
        try:
            value = load_json(path)
        except Exception as exc:
            value = {}
            issues.append({
                "code": f"INVALID_{name.upper()}",
                "blocking": True,
                "detail": str(exc),
            })
        if name == "stability":
            stability = value
        elif name == "snapshot":
            snapshot = value
        else:
            policy = value

    if not policy:
        issues.append({
            "code": "PERFORMANCE_POLICY_NOT_FOUND",
            "blocking": True,
            "detail": str(policy_path),
        })

    policy_safe = bool(policy.get("paper_only", False)) and all(
        policy.get(field) is False
        for field in (
            "broker_write_enabled",
            "order_submission_enabled",
            "live_trading_enabled",
            "external_network_enabled",
            "continuous_loop_enabled",
            "windows_task_enabled",
            "automatic_broker_execution_enabled",
        )
    )
    if not policy_safe:
        issues.append({
            "code": "PRODUCTION_READINESS_POLICY_UNSAFE",
            "blocking": True,
            "detail": "",
        })

    stability_ready = (
        stability.get("status") == "PASS"
        and stability.get("state") == "EXTENDED_PAPER_RUNTIME_READY"
        and stability.get("certificate_valid") is True
    )
    snapshot_available = bool(snapshot) and bool(
        snapshot.get("performance_snapshot_ready", False)
    )

    metrics: dict[str, Any] = {
        "total_trades": 0,
        "performance_score": 0.0,
        "performance_gate_passed": False,
        "checks": {},
        "checks_passed": 0,
        "checks_total": 0,
    }
    if snapshot_available:
        metrics, metric_issues = evaluate_metrics(snapshot, policy)
        issues.extend(metric_issues)

    blocking = any(item.get("blocking") for item in issues)
    evaluation_ready = stability_ready and snapshot_available and not blocking
    performance_passed = (
        evaluation_ready
        and metrics.get("performance_gate_passed") is True
        and metrics.get("performance_score", 0.0)
        >= finite_number(policy.get("minimum_performance_score"), 100.0)
    )

    performance_report = {
        "stage": "V83.89-V83.92",
        "state": (
            "PAPER_PERFORMANCE_EVALUATION_PASSED"
            if performance_passed
            else "PAPER_PERFORMANCE_EVALUATION_PENDING"
            if not blocking
            else "PAPER_PERFORMANCE_EVALUATION_BLOCKED"
        ),
        "stability_ready": stability_ready,
        "snapshot_available": snapshot_available,
        "evaluation_ready": evaluation_ready,
        "metrics": metrics,
        "paper_only": True,
        "observed_at": observed_at,
    }
    write_json(performance_report_path, performance_report)

    performance_certificate_written = False
    performance_certificate_valid = False
    if performance_passed:
        body = {
            "stage": "V83.92",
            "state": "PAPER_PERFORMANCE_CERTIFIED",
            "metrics": metrics,
            "stability_result_state": stability.get("state", ""),
            "paper_only": True,
            "certified_at": observed_at,
        }
        certificate = {
            **body,
            "certificate_sha256": digest_payload(body),
        }
        write_json(performance_certificate_path, certificate)
        performance_certificate_written = True
        performance_certificate_valid = (
            certificate["certificate_sha256"] == digest_payload(body)
        )

    risk_limits = {
        "stage": "V83.93-V83.95",
        "paper_only": True,
        "maximum_position_pct": finite_number(
            policy.get("maximum_position_pct"), 10.0
        ),
        "maximum_portfolio_exposure_pct": finite_number(
            policy.get("maximum_portfolio_exposure_pct"), 50.0
        ),
        "maximum_daily_loss_pct": finite_number(
            policy.get("maximum_daily_loss_pct"), 2.0
        ),
        "maximum_orders_per_day": int(policy.get("maximum_orders_per_day", 5)),
        "kill_switch_required": bool(policy.get("kill_switch_required", True)),
        "emergency_stop_required": bool(
            policy.get("emergency_stop_required", True)
        ),
        "duplicate_order_protection_required": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "external_network_enabled": False,
    }
    risk_checks = {
        "position_limit_positive": risk_limits["maximum_position_pct"] > 0,
        "position_limit_bounded": risk_limits["maximum_position_pct"] <= 100,
        "exposure_limit_positive": (
            risk_limits["maximum_portfolio_exposure_pct"] > 0
        ),
        "exposure_limit_bounded": (
            risk_limits["maximum_portfolio_exposure_pct"] <= 100
        ),
        "daily_loss_limit_positive": risk_limits["maximum_daily_loss_pct"] > 0,
        "daily_order_limit_positive": risk_limits["maximum_orders_per_day"] > 0,
        "kill_switch_required": risk_limits["kill_switch_required"],
        "emergency_stop_required": risk_limits["emergency_stop_required"],
        "broker_write_disabled": risk_limits["broker_write_enabled"] is False,
        "order_submission_disabled": (
            risk_limits["order_submission_enabled"] is False
        ),
    }
    risk_gate_passed = all(risk_checks.values()) and policy_safe
    risk_gate = {
        **risk_limits,
        "state": (
            "PRODUCTION_RISK_GATE_PASSED"
            if risk_gate_passed
            else "PRODUCTION_RISK_GATE_BLOCKED"
        ),
        "checks": risk_checks,
        "risk_gate_passed": risk_gate_passed,
        "observed_at": observed_at,
    }
    write_json(risk_gate_path, risk_gate)

    production_ready = (
        performance_passed
        and performance_certificate_valid
        and risk_gate_passed
        and not blocking
    )
    readiness_certificate_written = False
    readiness_certificate_valid = False
    if production_ready:
        body = {
            "stage": "V83.96",
            "state": "PRODUCTION_READINESS_APPROVED",
            "performance_certificate_valid": True,
            "risk_gate_passed": True,
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "approved_at": observed_at,
        }
        readiness = {**body, "certificate_sha256": digest_payload(body)}
        write_json(readiness_certificate_path, readiness)
        readiness_certificate_written = True
        readiness_certificate_valid = (
            readiness["certificate_sha256"] == digest_payload(body)
        )

    if blocking:
        state = "PRODUCTION_READINESS_BLOCKED"
        status = "BLOCKED"
    elif production_ready and readiness_certificate_valid:
        state = "PRODUCTION_READINESS_APPROVED"
        status = "PASS"
    else:
        state = "PRODUCTION_READINESS_PENDING"
        status = "PASS"

    dashboard = {
        "stage": "V83.96",
        "state": state,
        "status": status,
        "performance_production_readiness_state": state,
        "stability_ready": stability_ready,
        "snapshot_available": snapshot_available,
        "evaluation_ready": evaluation_ready,
        "performance_passed": performance_passed,
        "performance_certificate_written": performance_certificate_written,
        "performance_certificate_valid": performance_certificate_valid,
        "risk_gate_passed": risk_gate_passed,
        "production_ready": production_ready,
        "readiness_certificate_written": readiness_certificate_written,
        "readiness_certificate_valid": readiness_certificate_valid,
        "metrics": metrics,
        "risk_limits": risk_limits,
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
        "observed_at": observed_at,
    }
    write_json(dashboard_path, dashboard)

    result = {
        **dashboard,
        "stage_range": "V83.89-V83.96",
        "implementation_type": "PERFORMANCE_AND_PRODUCTION_READINESS",
        "actual_credentials_used": False,
        "actual_external_network_used": False,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "broker_command_execution_enabled": False,
        "issues": issues,
        "issue_count": len(issues),
        "blocking_issue_count": sum(
            1 for item in issues if item.get("blocking")
        ),
        "next_phase": (
            "V83_97_PAPER_PRODUCTION_RELEASE"
            if state == "PRODUCTION_READINESS_APPROVED"
            else "V83_89_TO_V83_96_AWAIT_PREREQUISITES"
            if status == "PASS"
            else "V83_89_TO_V83_96_RECOVER"
        ),
        "result_path": str(result_path.resolve()),
    }
    write_json(result_path, result)
    return result
