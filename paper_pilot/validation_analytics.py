from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if isinstance(value, dict):
            records.append(value)
    return records


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


class MultiDayValidationAnalytics:
    def run(
        self,
        *,
        policy_path: Path,
        validation_summary_path: Path,
        validation_gate_path: Path,
        validation_ledger_path: Path,
        analytics_path: Path,
        trend_path: Path,
        report_path: Path,
        dashboard_state_path: Path,
        result_path: Path,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        loaded = {}
        for name, path in (
            ("ANALYTICS_POLICY", policy_path),
            ("VALIDATION_SUMMARY", validation_summary_path),
            ("VALIDATION_GATE", validation_gate_path),
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
            if not payload:
                issues.append({
                    "code": f"{name}_NOT_FOUND",
                    "blocking": True,
                    "detail": str(path),
                })
            loaded[name] = payload

        policy = loaded["ANALYTICS_POLICY"]
        summary = loaded["VALIDATION_SUMMARY"]
        gate = loaded["VALIDATION_GATE"]

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
                    "TREND_LIMIT_INVALID",
                    5 <= int(policy.get("maximum_trend_points", 0)) <= 365,
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "analytics policy gate failed",
                    })
            policy_ready = all(passed for _, passed in checks)

        records = _read_jsonl(validation_ledger_path)
        records.sort(key=lambda item: str(item.get("validation_date", "")))
        maximum_points = int(policy.get("maximum_trend_points", 60) or 60)
        records = records[-maximum_points:]

        validation_days = int(summary.get("validation_days", len(records)) or 0)
        healthy_days = int(summary.get("healthy_days", 0) or 0)
        unhealthy_days = int(summary.get("unhealthy_days", 0) or 0)
        consecutive_healthy_days = int(
            summary.get("consecutive_healthy_days", 0) or 0
        )
        required_days = int(summary.get("minimum_validation_days", 0) or 0)
        required_consecutive = int(
            summary.get("minimum_consecutive_healthy_days", 0) or 0
        )
        validation_complete = bool(
            summary.get("validation_complete", False)
        )
        gate_clear = bool(gate.get("validation_gate_clear", False))

        progress_pct = (
            min(100.0, validation_days / required_days * 100)
            if required_days else 0.0
        )
        healthy_rate_pct = (
            healthy_days / validation_days * 100
            if validation_days else 0.0
        )
        unhealthy_rate_pct = (
            unhealthy_days / validation_days * 100
            if validation_days else 0.0
        )
        consecutive_progress_pct = (
            min(
                100.0,
                consecutive_healthy_days / required_consecutive * 100,
            )
            if required_consecutive else 0.0
        )

        equity_values = [
            _number(item.get("latest_equity", 0))
            for item in records
        ]
        return_values = [
            _number(item.get("cumulative_return_pct", 0))
            for item in records
        ]
        drawdown_values = [
            _number(item.get("max_drawdown_pct", 0))
            for item in records
        ]
        exposure_values = [
            _number(item.get("gross_exposure_pct", 0))
            for item in records
        ]

        average_return_pct = mean(return_values) if return_values else 0.0
        average_drawdown_pct = mean(drawdown_values) if drawdown_values else 0.0
        maximum_drawdown_pct = max(drawdown_values, default=0.0)
        average_exposure_pct = mean(exposure_values) if exposure_values else 0.0
        equity_change = (
            equity_values[-1] - equity_values[0]
            if len(equity_values) >= 2 else 0.0
        )
        equity_trend = (
            "UP" if equity_change > 0
            else "DOWN" if equity_change < 0
            else "FLAT"
        )

        trend = {
            "stage": "OP5.07",
            "points": [
                {
                    "validation_date": item.get("validation_date", ""),
                    "equity": _number(item.get("latest_equity", 0)),
                    "return_pct": _number(
                        item.get("cumulative_return_pct", 0)
                    ),
                    "drawdown_pct": _number(
                        item.get("max_drawdown_pct", 0)
                    ),
                    "exposure_pct": _number(
                        item.get("gross_exposure_pct", 0)
                    ),
                    "day_healthy": bool(item.get("day_healthy", False)),
                }
                for item in records
            ],
            "equity_trend": equity_trend,
            "equity_change": round(equity_change, 8),
            "paper_only": True,
        }
        _write(trend_path, trend)

        analytics = {
            "stage": "OP5.05",
            "validation_days": validation_days,
            "healthy_days": healthy_days,
            "unhealthy_days": unhealthy_days,
            "consecutive_healthy_days": consecutive_healthy_days,
            "progress_pct": round(progress_pct, 8),
            "healthy_rate_pct": round(healthy_rate_pct, 8),
            "unhealthy_rate_pct": round(unhealthy_rate_pct, 8),
            "consecutive_progress_pct": round(
                consecutive_progress_pct, 8
            ),
            "average_return_pct": round(average_return_pct, 8),
            "average_drawdown_pct": round(average_drawdown_pct, 8),
            "maximum_drawdown_pct": round(maximum_drawdown_pct, 8),
            "average_exposure_pct": round(average_exposure_pct, 8),
            "equity_trend": equity_trend,
            "validation_complete": validation_complete,
            "validation_gate_clear": gate_clear,
            "paper_only": True,
        }
        _write(analytics_path, analytics)

        if any(item.get("blocking") for item in issues):
            state, status = "VALIDATION_ANALYTICS_SAFE_MODE", "BLOCKED"
        elif validation_days == 0:
            state, status = "WAIT_VALIDATION_DATA", "PASS"
        elif validation_complete and gate_clear:
            state, status = "VALIDATION_ANALYTICS_COMPLETE", "PASS"
        else:
            state, status = "VALIDATION_ANALYTICS_IN_PROGRESS", "PASS"

        observed_at = datetime.now(timezone.utc).isoformat()
        report = {
            "stage": "OP5.08",
            "state": state,
            "validation_days": validation_days,
            "required_validation_days": required_days,
            "healthy_days": healthy_days,
            "unhealthy_days": unhealthy_days,
            "healthy_rate_pct": round(healthy_rate_pct, 8),
            "consecutive_healthy_days": consecutive_healthy_days,
            "required_consecutive_healthy_days": required_consecutive,
            "progress_pct": round(progress_pct, 8),
            "average_return_pct": round(average_return_pct, 8),
            "maximum_drawdown_pct": round(maximum_drawdown_pct, 8),
            "equity_trend": equity_trend,
            "validation_complete": validation_complete,
            "validation_gate_clear": gate_clear,
            "gate_reasons": gate.get("gate_reasons", []),
            "paper_only": True,
            "created_at": observed_at,
        }
        _write(report_path, report)

        dashboard = {
            "stage": "OP5.06",
            "analytics_state": state,
            **analytics,
            "trend_point_count": len(records),
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "observed_at": observed_at,
        }
        _write(dashboard_state_path, dashboard)

        blocking = sum(
            1 for item in issues if item.get("blocking")
        )
        result = {
            "stage_range": "OP5.05-OP5.08",
            "implementation_type": (
                "MULTI_DAY_VALIDATION_ANALYTICS"
            ),
            "status": status,
            "state": state,
            "validation_days": validation_days,
            "healthy_days": healthy_days,
            "unhealthy_days": unhealthy_days,
            "consecutive_healthy_days": consecutive_healthy_days,
            "progress_pct": round(progress_pct, 8),
            "healthy_rate_pct": round(healthy_rate_pct, 8),
            "unhealthy_rate_pct": round(unhealthy_rate_pct, 8),
            "average_return_pct": round(average_return_pct, 8),
            "average_drawdown_pct": round(average_drawdown_pct, 8),
            "maximum_drawdown_pct": round(maximum_drawdown_pct, 8),
            "average_exposure_pct": round(average_exposure_pct, 8),
            "equity_trend": equity_trend,
            "trend_point_count": len(records),
            "validation_complete": validation_complete,
            "validation_gate_clear": gate_clear,
            "analytics_written": True,
            "trend_written": True,
            "report_written": True,
            "dashboard_state_written": True,
            "paper_only": True,
            "read_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "cancel_enabled": False,
            "position_close_enabled": False,
            "continuous_loop_enabled": False,
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
                "OP5_09_TO_OP5_12_VALIDATION_CERTIFICATE"
                if validation_complete and gate_clear
                else "OP5_05_TO_OP5_08_CONTINUE_ANALYTICS"
            ),
            "validation_mode": "LOCAL_VALIDATION_ANALYTICS_ONLY",
            "observed_at": observed_at,
            "result_path": str(result_path.resolve()),
        }
        _write(result_path, result)
        return result
