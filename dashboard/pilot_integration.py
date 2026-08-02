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


def build_pilot_payload(root: Path) -> dict[str, Any]:
    state = _load(
        root
        / "release/op4_01_to_op4_04/actual/"
        "paper_pilot_dashboard_state.json"
    )
    return {
        "dashboard_stage": "OP4.01-OP4.04",
        "pilot_id": state.get("pilot_id", ""),
        "session_id": state.get("session_id", ""),
        "pilot_name": state.get("pilot_name", ""),
        "pilot_status": state.get(
            "pilot_status", "NOT_AVAILABLE"
        ),
        "pilot_state": state.get(
            "pilot_state", "NOT_AVAILABLE"
        ),
        "start_gate_ready": bool(
            state.get("start_gate_ready", False)
        ),
        "pilot_started": bool(
            state.get("pilot_started", False)
        ),
        "duplicate_pilot": bool(
            state.get("duplicate_pilot", False)
        ),
        "open_order_count": int(
            state.get("open_order_count", 0) or 0
        ),
        "open_orders_clear": bool(
            state.get("open_orders_clear", False)
        ),
        "position_count": int(
            state.get("position_count", 0) or 0
        ),
        "recovery_required": bool(
            state.get("recovery_required", False)
        ),
        "emergency_stop_engaged": bool(
            state.get(
                "emergency_stop_engaged", False
            )
        ),
        "paper_account_ready": bool(
            state.get("paper_account_ready", False)
        ),
        "started_at": state.get("started_at", ""),
        "paper_only": True,
        "broker_write_enabled": False,
        "live_trading_enabled": False,
    }
