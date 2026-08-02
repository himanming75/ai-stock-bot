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


def _append(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")


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


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


class PaperPilotPerformanceCollector:
    def run(
        self,
        *,
        policy_path: Path,
        foundation_result_path: Path,
        session_monitor_result_path: Path,
        current_snapshot_path: Path,
        trade_ledger_path: Path,
        equity_history_path: Path,
        daily_report_path: Path,
        performance_report_path: Path,
        dashboard_state_path: Path,
        result_path: Path,
        collect_snapshot: bool = False,
        observed_at: str | None = None,
    ) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []

        loaded: dict[str, dict[str, Any]] = {}
        for name, path, required in (
            ("PERFORMANCE_POLICY", policy_path, True),
            ("FOUNDATION_RESULT", foundation_result_path, True),
            ("SESSION_MONITOR_RESULT", session_monitor_result_path, True),
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

        policy = loaded["PERFORMANCE_POLICY"]
        foundation = loaded["FOUNDATION_RESULT"]
        monitor = loaded["SESSION_MONITOR_RESULT"]
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
                    "MIN_SAMPLE_INVALID",
                    1 <= int(policy.get("minimum_samples_for_metrics", 0)) <= 100,
                ),
                (
                    "MAX_HISTORY_INVALID",
                    10 <= int(policy.get("maximum_history_records", 0)) <= 10000,
                ),
            ]
            for code, passed in checks:
                if not passed:
                    issues.append({
                        "code": code,
                        "blocking": True,
                        "detail": "performance policy gate failed",
                    })
            policy_ready = all(passed for _, passed in checks)

        pilot_started = bool(foundation.get("pilot_started", False))
        pilot_id = str(foundation.get("pilot_id", "")).strip()
        session_id = str(foundation.get("session_id", "")).strip()
        session_health = str(monitor.get("health_status", "WAITING")).upper()

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
        equity = _number(account.get("equity", 0))
        portfolio_value = _number(account.get("portfolio_value", equity))
        cash = _number(account.get("cash", 0))
        buying_power = _number(account.get("buying_power", 0))
        positions = snapshot.get("positions", [])
        if not isinstance(positions, list):
            positions = []

        now = observed_at or datetime.now(timezone.utc).isoformat()
        history = _read_jsonl(equity_history_path)

        sample_written = False
        if (
            collect_snapshot
            and pilot_started
            and policy_ready
            and snapshot_actual
            and not any(i.get("blocking") for i in issues)
        ):
            previous = history[-1] if history else {}
            previous_equity = _number(previous.get("equity", equity))
            pnl_change = equity - previous_equity
            return_pct = (
                (pnl_change / previous_equity) * 100
                if previous_equity
                else 0.0
            )
            sample = {
                "stage": "OP4.09",
                "pilot_id": pilot_id,
                "session_id": session_id,
                "observed_at": now,
                "equity": equity,
                "portfolio_value": portfolio_value,
                "cash": cash,
                "buying_power": buying_power,
                "position_count": len(positions),
                "pnl_change": round(pnl_change, 8),
                "return_pct": round(return_pct, 8),
                "paper_only": True,
            }
            _append(equity_history_path, sample)
            history.append(sample)
            max_records = int(policy["maximum_history_records"])
            if len(history) > max_records:
                trimmed = history[-max_records:]
                equity_history_path.write_text(
                    "".join(json.dumps(item, sort_keys=True) + "\n" for item in trimmed),
                    encoding="utf-8",
                )
                history = trimmed
            sample_written = True

        trades = _read_jsonl(trade_ledger_path)
        realized_values = [
            _number(item.get("realized_pnl", item.get("pnl", 0)))
            for item in trades
        ]
        wins = sum(1 for value in realized_values if value > 0)
        losses = sum(1 for value in realized_values if value < 0)
        breakeven = sum(1 for value in realized_values if value == 0)
        total_trades = len(realized_values)
        total_realized_pnl = sum(realized_values)
        avg_win = (
            sum(value for value in realized_values if value > 0) / wins
            if wins else 0.0
        )
        avg_loss = (
            sum(value for value in realized_values if value < 0) / losses
            if losses else 0.0
        )
        win_rate = (wins / total_trades * 100) if total_trades else 0.0

        equity_values = [_number(item.get("equity", 0)) for item in history]
        initial_equity = equity_values[0] if equity_values else equity
        latest_equity = equity_values[-1] if equity_values else equity
        cumulative_pnl = latest_equity - initial_equity if equity_values else 0.0
        cumulative_return_pct = (
            cumulative_pnl / initial_equity * 100
            if initial_equity else 0.0
        )

        peak = None
        max_drawdown = 0.0
        max_drawdown_pct = 0.0
        for value in equity_values:
            peak = value if peak is None else max(peak, value)
            drawdown = (peak - value) if peak is not None else 0.0
            drawdown_pct = (drawdown / peak * 100) if peak else 0.0
            max_drawdown = max(max_drawdown, drawdown)
            max_drawdown_pct = max(max_drawdown_pct, drawdown_pct)

        minimum_samples = int(policy.get("minimum_samples_for_metrics", 1) or 1)
        metrics_ready = len(history) >= minimum_samples

        daily_report = {
            "stage": "OP4.10",
            "pilot_id": pilot_id,
            "session_id": session_id,
            "report_date": str(now)[:10],
            "sample_count": len(history),
            "trade_count": total_trades,
            "wins": wins,
            "losses": losses,
            "breakeven": breakeven,
            "win_rate_pct": round(win_rate, 8),
            "average_win": round(avg_win, 8),
            "average_loss": round(avg_loss, 8),
            "total_realized_pnl": round(total_realized_pnl, 8),
            "latest_equity": round(latest_equity, 8),
            "cumulative_pnl": round(cumulative_pnl, 8),
            "cumulative_return_pct": round(cumulative_return_pct, 8),
            "max_drawdown": round(max_drawdown, 8),
            "max_drawdown_pct": round(max_drawdown_pct, 8),
            "metrics_ready": metrics_ready,
            "paper_only": True,
            "created_at": now,
        }
        _write(daily_report_path, daily_report)

        performance_report = {
            "stage": "OP4.11",
            "pilot_id": pilot_id,
            "session_id": session_id,
            "pilot_started": pilot_started,
            "session_health": session_health,
            "sample_written": sample_written,
            "sample_count": len(history),
            "trade_count": total_trades,
            "win_rate_pct": round(win_rate, 8),
            "total_realized_pnl": round(total_realized_pnl, 8),
            "initial_equity": round(initial_equity, 8),
            "latest_equity": round(latest_equity, 8),
            "cumulative_pnl": round(cumulative_pnl, 8),
            "cumulative_return_pct": round(cumulative_return_pct, 8),
            "max_drawdown": round(max_drawdown, 8),
            "max_drawdown_pct": round(max_drawdown_pct, 8),
            "metrics_ready": metrics_ready,
            "paper_only": True,
            "read_only": True,
            "created_at": now,
        }
        _write(performance_report_path, performance_report)

        if any(i.get("blocking") for i in issues):
            state, status = "PAPER_PERFORMANCE_COLLECTOR_SAFE_MODE", "BLOCKED"
        elif not pilot_started:
            state, status = "WAIT_PILOT_START", "PASS"
        elif sample_written:
            state, status = "PAPER_PERFORMANCE_SAMPLE_COLLECTED", "PASS"
        else:
            state, status = "PAPER_PERFORMANCE_READY", "PASS"

        dashboard = {
            "stage": "OP4.12",
            "pilot_id": pilot_id,
            "session_id": session_id,
            "collector_state": state,
            "pilot_started": pilot_started,
            "session_health": session_health,
            "sample_count": len(history),
            "trade_count": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate_pct": round(win_rate, 8),
            "latest_equity": round(latest_equity, 8),
            "cumulative_pnl": round(cumulative_pnl, 8),
            "cumulative_return_pct": round(cumulative_return_pct, 8),
            "max_drawdown_pct": round(max_drawdown_pct, 8),
            "metrics_ready": metrics_ready,
            "paper_only": True,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "observed_at": now,
        }
        _write(dashboard_state_path, dashboard)

        blocking = sum(1 for item in issues if item.get("blocking"))
        result = {
            "stage_range": "OP4.09-OP4.12",
            "implementation_type": "PAPER_PILOT_PERFORMANCE_COLLECTOR",
            "status": status,
            "state": state,
            "pilot_id": pilot_id,
            "session_id": session_id,
            "pilot_started": pilot_started,
            "session_health": session_health,
            "collect_snapshot_requested": collect_snapshot,
            "sample_written": sample_written,
            "sample_count": len(history),
            "trade_count": total_trades,
            "wins": wins,
            "losses": losses,
            "breakeven": breakeven,
            "win_rate_pct": round(win_rate, 8),
            "average_win": round(avg_win, 8),
            "average_loss": round(avg_loss, 8),
            "total_realized_pnl": round(total_realized_pnl, 8),
            "initial_equity": round(initial_equity, 8),
            "latest_equity": round(latest_equity, 8),
            "cumulative_pnl": round(cumulative_pnl, 8),
            "cumulative_return_pct": round(cumulative_return_pct, 8),
            "max_drawdown": round(max_drawdown, 8),
            "max_drawdown_pct": round(max_drawdown_pct, 8),
            "metrics_ready": metrics_ready,
            "daily_report_written": True,
            "performance_report_written": True,
            "dashboard_state_written": True,
            "paper_only": True,
            "read_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "cancel_enabled": False,
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
                "OP4_13_PAPER_RISK_MONITOR"
                if pilot_started
                else "OP4_09_TO_OP4_12_WAIT_PILOT_START"
            ),
            "validation_mode": "LOCAL_PAPER_PERFORMANCE_COLLECTION_ONLY",
            "observed_at": now,
            "result_path": str(result_path.resolve()),
        }
        _write(result_path, result)
        return result
