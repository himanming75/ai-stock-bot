from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


class PaperPilotRiskMonitor:
    def run(
        self,
        *,
        policy_path: Path,
        foundation_result_path: Path,
        session_monitor_result_path: Path,
        performance_result_path: Path,
        current_snapshot_path: Path,
        drawdown_report_path: Path,
        exposure_report_path: Path,
        daily_loss_report_path: Path,
        emergency_stop_gate_path: Path,
        dashboard_state_path: Path,
        result_path: Path,
        observed_at: str | None = None,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        loaded: dict[str, dict[str, Any]] = {}
        for name, path, required in (
            ("RISK_POLICY", policy_path, True),
            ("FOUNDATION_RESULT", foundation_result_path, True),
            ("SESSION_MONITOR_RESULT", session_monitor_result_path, True),
            ("PERFORMANCE_RESULT", performance_result_path, True),
            ("CURRENT_PAPER_SNAPSHOT", current_snapshot_path, True),
        ):
            try:
                payload = _load(path)
            except Exception as exc:
                payload = {}
                issues.append({
                    "code": f"INVALID_{name}",
                    "blocking": True,
                    "detail": str(exc),
                })
            if required and not payload:
                issues.append({
                    "code": f"{name}_NOT_FOUND",
                    "blocking": True,
                    "detail": str(path),
                })
            loaded[name] = payload

        policy = loaded["RISK_POLICY"]
        foundation = loaded["FOUNDATION_RESULT"]
        session = loaded["SESSION_MONITOR_RESULT"]
        performance = loaded["PERFORMANCE_RESULT"]
        snapshot = loaded["CURRENT_PAPER_SNAPSHOT"]

        policy_ready = False
        if policy:
            checks = [
                ("PAPER_ONLY_REQUIRED", bool(policy.get("paper_only", False))),
                ("READ_ONLY_REQUIRED", bool(policy.get("read_only", False))),
                (
                    "BROKER_WRITE_MUST_BE_DISABLED",
                    not bool(policy.get("broker_write_enabled", True)),
                ),
                (
                    "LIVE_TRADING_MUST_BE_DISABLED",
                    not bool(policy.get("live_trading_enabled", True)),
                ),
                (
                    "MAX_DRAWDOWN_INVALID",
                    0 < float(policy.get("maximum_drawdown_pct", 0)) <= 25,
                ),
                (
                    "MAX_DAILY_LOSS_INVALID",
                    0 < float(policy.get("maximum_daily_loss_pct", 0)) <= 10,
                ),
                (
                    "MAX_GROSS_EXPOSURE_INVALID",
                    0 < float(policy.get("maximum_gross_exposure_pct", 0)) <= 200,
                ),
                (
                    "MAX_SYMBOL_EXPOSURE_INVALID",
                    0 < float(policy.get("maximum_symbol_exposure_pct", 0)) <= 100,
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "risk policy gate failed",
                    })
            policy_ready = all(passed for _, passed in checks)

        pilot_started = bool(foundation.get("pilot_started", False))
        pilot_id = str(foundation.get("pilot_id", "")).strip()
        session_id = str(foundation.get("session_id", "")).strip()
        session_health = str(session.get("health_status", "WAITING")).upper()
        session_timeout = bool(session.get("timeout_detected", False))
        session_stop_required = bool(
            session.get("controlled_stop_required", False)
        )

        snapshot_actual = bool(
            snapshot.get("snapshot_type") == "ACTUAL_ALPACA_PAPER_READ_ONLY"
            and snapshot.get("paper_only") is True
            and snapshot.get("read_only") is True
        )
        if snapshot and not snapshot_actual:
            issues.append({
                "code": "ACTUAL_PAPER_SNAPSHOT_REQUIRED",
                "blocking": True,
                "detail": str(snapshot.get("snapshot_type", "")),
            })

        account = snapshot.get("account", {})
        if not isinstance(account, dict):
            account = {}
        positions = snapshot.get("positions", [])
        if not isinstance(positions, list):
            positions = []

        equity = _number(account.get("equity", 0))
        portfolio_value = _number(account.get("portfolio_value", equity))
        cash = _number(account.get("cash", 0))

        initial_equity = _number(performance.get("initial_equity", equity))
        latest_equity = _number(performance.get("latest_equity", equity))
        max_drawdown_pct = _number(performance.get("max_drawdown_pct", 0))
        cumulative_return_pct = _number(
            performance.get("cumulative_return_pct", 0)
        )

        current_drawdown = max(
            0.0,
            ((initial_equity - latest_equity) / initial_equity * 100)
            if initial_equity else 0.0,
        )
        effective_drawdown_pct = max(max_drawdown_pct, current_drawdown)

        gross_market_value = 0.0
        symbol_exposures: list[dict[str, Any]] = []
        for item in positions:
            if not isinstance(item, dict):
                continue
            market_value = abs(_number(item.get("market_value", 0)))
            gross_market_value += market_value
            exposure_pct = (
                market_value / portfolio_value * 100
                if portfolio_value else 0.0
            )
            symbol_exposures.append({
                "symbol": str(item.get("symbol", "")),
                "market_value": round(market_value, 8),
                "exposure_pct": round(exposure_pct, 8),
            })

        gross_exposure_pct = (
            gross_market_value / portfolio_value * 100
            if portfolio_value else 0.0
        )
        maximum_symbol_exposure_pct = max(
            (
                _number(item.get("exposure_pct", 0))
                for item in symbol_exposures
            ),
            default=0.0,
        )
        cash_pct = (
            cash / portfolio_value * 100
            if portfolio_value else 0.0
        )

        daily_loss_pct = max(0.0, -cumulative_return_pct)

        risk_reasons: list[str] = []
        if effective_drawdown_pct >= float(policy.get("maximum_drawdown_pct", 0)):
            risk_reasons.append("MAX_DRAWDOWN_EXCEEDED")
        if daily_loss_pct >= float(policy.get("maximum_daily_loss_pct", 0)):
            risk_reasons.append("MAX_DAILY_LOSS_EXCEEDED")
        if gross_exposure_pct >= float(
            policy.get("maximum_gross_exposure_pct", 0)
        ):
            risk_reasons.append("MAX_GROSS_EXPOSURE_EXCEEDED")
        if maximum_symbol_exposure_pct >= float(
            policy.get("maximum_symbol_exposure_pct", 0)
        ):
            risk_reasons.append("MAX_SYMBOL_EXPOSURE_EXCEEDED")
        if session_timeout:
            risk_reasons.append("SESSION_TIMEOUT")
        if session_stop_required:
            risk_reasons.append("SESSION_CONTROLLED_STOP_REQUIRED")
        if session_health in {"STOP_REQUIRED", "TIMEOUT", "DEGRADED"}:
            risk_reasons.append("SESSION_HEALTH_UNSAFE")
        if not snapshot_actual:
            risk_reasons.append("ACTUAL_PAPER_SNAPSHOT_INVALID")

        emergency_stop_required = bool(
            pilot_started and risk_reasons
        )

        now = observed_at or datetime.now(timezone.utc).isoformat()

        _write(drawdown_report_path, {
            "stage": "OP4.13",
            "pilot_id": pilot_id,
            "session_id": session_id,
            "initial_equity": initial_equity,
            "latest_equity": latest_equity,
            "current_drawdown_pct": round(current_drawdown, 8),
            "historical_max_drawdown_pct": round(max_drawdown_pct, 8),
            "effective_drawdown_pct": round(effective_drawdown_pct, 8),
            "maximum_drawdown_pct": float(
                policy.get("maximum_drawdown_pct", 0)
            ),
            "threshold_exceeded": (
                effective_drawdown_pct
                >= float(policy.get("maximum_drawdown_pct", 0))
            ),
            "paper_only": True,
            "observed_at": now,
        })

        _write(exposure_report_path, {
            "stage": "OP4.14",
            "pilot_id": pilot_id,
            "session_id": session_id,
            "portfolio_value": portfolio_value,
            "cash": cash,
            "cash_pct": round(cash_pct, 8),
            "gross_market_value": round(gross_market_value, 8),
            "gross_exposure_pct": round(gross_exposure_pct, 8),
            "maximum_symbol_exposure_pct": round(
                maximum_symbol_exposure_pct, 8
            ),
            "position_count": len(symbol_exposures),
            "symbol_exposures": symbol_exposures,
            "gross_exposure_threshold_pct": float(
                policy.get("maximum_gross_exposure_pct", 0)
            ),
            "symbol_exposure_threshold_pct": float(
                policy.get("maximum_symbol_exposure_pct", 0)
            ),
            "paper_only": True,
            "observed_at": now,
        })

        _write(daily_loss_report_path, {
            "stage": "OP4.15",
            "pilot_id": pilot_id,
            "session_id": session_id,
            "cumulative_return_pct": round(cumulative_return_pct, 8),
            "daily_loss_pct": round(daily_loss_pct, 8),
            "maximum_daily_loss_pct": float(
                policy.get("maximum_daily_loss_pct", 0)
            ),
            "threshold_exceeded": (
                daily_loss_pct
                >= float(policy.get("maximum_daily_loss_pct", 0))
            ),
            "paper_only": True,
            "observed_at": now,
        })

        _write(emergency_stop_gate_path, {
            "stage": "OP4.16",
            "pilot_id": pilot_id,
            "session_id": session_id,
            "pilot_started": pilot_started,
            "session_health": session_health,
            "emergency_stop_required": emergency_stop_required,
            "risk_reasons": risk_reasons,
            "broker_action_performed": False,
            "order_cancel_performed": False,
            "position_close_performed": False,
            "paper_only": True,
            "created_at": now,
        })

        if any(i.get("blocking") for i in issues):
            state, status = "PAPER_RISK_MONITOR_SAFE_MODE", "BLOCKED"
        elif not pilot_started:
            state, status = "WAIT_PILOT_START", "PASS"
        elif emergency_stop_required:
            state, status = "EMERGENCY_STOP_REQUIRED", "PASS"
        else:
            state, status = "PAPER_RISK_HEALTHY", "PASS"

        _write(dashboard_state_path, {
            "stage": "OP4.13-OP4.16",
            "pilot_id": pilot_id,
            "session_id": session_id,
            "risk_state": state,
            "session_health": session_health,
            "pilot_started": pilot_started,
            "current_drawdown_pct": round(current_drawdown, 8),
            "max_drawdown_pct": round(effective_drawdown_pct, 8),
            "daily_loss_pct": round(daily_loss_pct, 8),
            "gross_exposure_pct": round(gross_exposure_pct, 8),
            "maximum_symbol_exposure_pct": round(
                maximum_symbol_exposure_pct, 8
            ),
            "position_count": len(symbol_exposures),
            "emergency_stop_required": emergency_stop_required,
            "risk_reasons": risk_reasons,
            "paper_only": True,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "observed_at": now,
        })

        blocking = sum(1 for item in issues if item.get("blocking"))
        result = {
            "stage_range": "OP4.13-OP4.16",
            "implementation_type": "PAPER_PILOT_RISK_MONITOR",
            "status": status,
            "state": state,
            "pilot_id": pilot_id,
            "session_id": session_id,
            "pilot_started": pilot_started,
            "session_health": session_health,
            "current_drawdown_pct": round(current_drawdown, 8),
            "max_drawdown_pct": round(effective_drawdown_pct, 8),
            "daily_loss_pct": round(daily_loss_pct, 8),
            "gross_exposure_pct": round(gross_exposure_pct, 8),
            "maximum_symbol_exposure_pct": round(
                maximum_symbol_exposure_pct, 8
            ),
            "position_count": len(symbol_exposures),
            "emergency_stop_required": emergency_stop_required,
            "risk_reasons": risk_reasons,
            "drawdown_report_written": True,
            "exposure_report_written": True,
            "daily_loss_report_written": True,
            "emergency_stop_gate_written": True,
            "dashboard_state_written": True,
            "paper_only": True,
            "read_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "cancel_enabled": False,
            "position_close_enabled": False,
            "replace_enabled": False,
            "live_trading_enabled": False,
            "actual_credentials_used": False,
            "actual_external_network_used": False,
            "network_requests_executed": 0,
            "write_requests_executed": 0,
            "actual_paper_orders_submitted": 0,
            "live_orders_submitted": 0,
            "safe_mode_engaged": blocking > 0,
            "issue_count": len(issues),
            "blocking_issue_count": blocking,
            "issues": issues,
            "next_phase": (
                "OP4_17_PILOT_AUTOMATION"
                if pilot_started and not emergency_stop_required
                else "OP4_13_TO_OP4_16_WAIT_OR_STOP"
            ),
            "validation_mode": "LOCAL_PAPER_RISK_MONITOR_ONLY",
            "observed_at": now,
            "result_path": str(result_path.resolve()),
        }
        _write(result_path, result)
        return result
