from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def build_pilot_performance_payload(root: Path) -> dict[str, Any]:
    state = _load(
        root
        / "release/op4_09_to_op4_12/actual/"
        "paper_performance_dashboard_state.json"
    )
    return {
        "dashboard_stage": "OP4.09-OP4.12",
        "collector_state": state.get("collector_state", "NOT_AVAILABLE"),
        "pilot_id": state.get("pilot_id", ""),
        "session_id": state.get("session_id", ""),
        "pilot_started": bool(state.get("pilot_started", False)),
        "session_health": state.get("session_health", "NOT_AVAILABLE"),
        "sample_count": int(state.get("sample_count", 0) or 0),
        "trade_count": int(state.get("trade_count", 0) or 0),
        "wins": int(state.get("wins", 0) or 0),
        "losses": int(state.get("losses", 0) or 0),
        "win_rate_pct": float(state.get("win_rate_pct", 0) or 0),
        "latest_equity": float(state.get("latest_equity", 0) or 0),
        "cumulative_pnl": float(state.get("cumulative_pnl", 0) or 0),
        "cumulative_return_pct": float(
            state.get("cumulative_return_pct", 0) or 0
        ),
        "max_drawdown_pct": float(
            state.get("max_drawdown_pct", 0) or 0
        ),
        "metrics_ready": bool(state.get("metrics_ready", False)),
        "paper_only": True,
        "broker_write_enabled": False,
        "live_trading_enabled": False,
    }
