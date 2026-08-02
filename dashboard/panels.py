from __future__ import annotations

from typing import Any


def runtime_panel(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    runtime = sources.get("runtime", {})
    heartbeat = sources.get("heartbeat", {})
    return {
        "state": runtime.get("state", "NO_RUNTIME_DATA"),
        "status": runtime.get("status", "UNKNOWN"),
        "safe_mode": bool(runtime.get("safe_mode_engaged", False)),
        "runtime_id": runtime.get("runtime_id", ""),
        "pipeline_id": runtime.get("pipeline_id", ""),
        "heartbeat_status": heartbeat.get("heartbeat_status", "NOT_AVAILABLE"),
        "heartbeat_at": heartbeat.get("heartbeat_at", ""),
        "single_tick_only": bool(runtime.get("single_tick_only", True)),
        "continuous_loop_enabled": bool(
            runtime.get("continuous_loop_enabled", False)
        ),
    }


def portfolio_panel(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    snapshot = sources.get("portfolio", {})
    account = snapshot.get("account", {})
    if not isinstance(account, dict):
        account = {}
    return {
        "status": account.get("status", "NOT_AVAILABLE"),
        "cash": _number(account.get("cash", 0)),
        "buying_power": _number(account.get("buying_power", 0)),
        "portfolio_value": _number(account.get("portfolio_value", 0)),
        "equity": _number(account.get("equity", 0)),
        "open_order_count": len(snapshot.get("open_orders", []))
        if isinstance(snapshot.get("open_orders", []), list)
        else 0,
        "position_count": len(snapshot.get("positions", []))
        if isinstance(snapshot.get("positions", []), list)
        else 0,
    }


def signal_panel(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    signal = sources.get("signal", {})
    pipeline = sources.get("pipeline", {})
    return {
        "symbol": signal.get("symbol", pipeline.get("symbol", "")),
        "requested_action": signal.get(
            "requested_action", pipeline.get("requested_action", "")
        ),
        "approved_action": signal.get(
            "approved_action", pipeline.get("approved_action", "HOLD")
        ),
        "confidence": _number(
            signal.get("confidence", pipeline.get("confidence", 0))
        ),
        "quantity": int(
            signal.get(
                "approved_quantity",
                pipeline.get("approved_quantity", 0),
            )
            or 0
        ),
        "reference_price": _number(signal.get("reference_price", 0)),
        "reasons": signal.get(
            "pipeline_reasons", pipeline.get("pipeline_reasons", [])
        ),
        "created_at": signal.get("created_at", ""),
        "pipeline_state": pipeline.get("state", "NO_PIPELINE_DATA"),
    }


def daily_report_panel(
    sources: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    report = sources.get("daily_report", {})
    runtime = sources.get("runtime", {})
    return {
        "signal_count": int(
            report.get("signal_count", runtime.get("signal_count", 0)) or 0
        ),
        "buy_count": int(
            report.get("buy_count", runtime.get("buy_count", 0)) or 0
        ),
        "sell_count": int(
            report.get("sell_count", runtime.get("sell_count", 0)) or 0
        ),
        "hold_count": int(
            report.get("hold_count", runtime.get("hold_count", 0)) or 0
        ),
        "risk_block_count": int(
            report.get(
                "risk_block_count", runtime.get("risk_block_count", 0)
            )
            or 0
        ),
        "error_count": int(
            report.get("error_count", runtime.get("error_count", 0)) or 0
        ),
        "total_pnl": _number(
            report.get("total_pnl", runtime.get("total_pnl", 0))
        ),
        "max_drawdown_pct": _number(
            report.get(
                "max_drawdown_pct",
                runtime.get("max_drawdown_pct", 0),
            )
        ),
        "runtime_seconds": int(
            report.get(
                "runtime_seconds", runtime.get("runtime_seconds", 0)
            )
            or 0
        ),
        "report_ready": bool(
            report.get(
                "daily_shadow_report_ready",
                runtime.get("daily_shadow_report_written", False),
            )
        ),
    }


def build_dashboard_payload(
    sources: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    runtime = runtime_panel(sources)
    return {
        "application": "AI Stock Bot",
        "dashboard_stage": "DASH1.01-DASH1.04",
        "read_only": True,
        "order_submission_enabled": False,
        "broker_write_enabled": False,
        "live_trading_enabled": False,
        "runtime": runtime,
        "portfolio": portfolio_panel(sources),
        "signal": signal_panel(sources),
        "daily_report": daily_report_panel(sources),
        "dashboard_state": (
            "SAFE_MODE"
            if runtime["safe_mode"]
            else "READY"
        ),
    }


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
