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


def build_pilot_risk_payload(root: Path) -> dict[str, Any]:
    state = _load(
        root
        / "release/op4_13_to_op4_16/actual/"
        "paper_risk_dashboard_state.json"
    )
    return {
        "dashboard_stage": "OP4.13-OP4.16",
        "risk_state": state.get("risk_state", "NOT_AVAILABLE"),
        "pilot_id": state.get("pilot_id", ""),
        "session_id": state.get("session_id", ""),
        "session_health": state.get("session_health", "NOT_AVAILABLE"),
        "pilot_started": bool(state.get("pilot_started", False)),
        "current_drawdown_pct": float(
            state.get("current_drawdown_pct", 0) or 0
        ),
        "max_drawdown_pct": float(
            state.get("max_drawdown_pct", 0) or 0
        ),
        "daily_loss_pct": float(
            state.get("daily_loss_pct", 0) or 0
        ),
        "gross_exposure_pct": float(
            state.get("gross_exposure_pct", 0) or 0
        ),
        "maximum_symbol_exposure_pct": float(
            state.get("maximum_symbol_exposure_pct", 0) or 0
        ),
        "position_count": int(
            state.get("position_count", 0) or 0
        ),
        "emergency_stop_required": bool(
            state.get("emergency_stop_required", False)
        ),
        "risk_reasons": (
            state.get("risk_reasons", [])
            if isinstance(state.get("risk_reasons"), list)
            else []
        ),
        "paper_only": True,
        "broker_write_enabled": False,
        "live_trading_enabled": False,
    }
