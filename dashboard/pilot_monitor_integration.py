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


def build_pilot_monitor_payload(
    root: Path,
) -> dict[str, Any]:
    state = _load(
        root
        / "release/op4_05_to_op4_08/actual/"
        "paper_session_monitor_dashboard_state.json"
    )
    return {
        "dashboard_stage": "OP4.05-OP4.08",
        "pilot_id": state.get("pilot_id", ""),
        "session_id": state.get("session_id", ""),
        "monitor_state": state.get(
            "monitor_state", "NOT_AVAILABLE"
        ),
        "health_status": state.get(
            "health_status", "NOT_AVAILABLE"
        ),
        "heartbeat_written": bool(
            state.get("heartbeat_written", False)
        ),
        "tick_number": int(
            state.get("tick_number", 0) or 0
        ),
        "heartbeat_age_seconds": state.get(
            "heartbeat_age_seconds"
        ),
        "timeout_detected": bool(
            state.get("timeout_detected", False)
        ),
        "controlled_stop_required": bool(
            state.get(
                "controlled_stop_required", False
            )
        ),
        "controlled_stop_written": bool(
            state.get(
                "controlled_stop_written", False
            )
        ),
        "stop_reasons": (
            state.get("stop_reasons", [])
            if isinstance(state.get("stop_reasons"), list)
            else []
        ),
        "paper_only": True,
        "broker_write_enabled": False,
        "live_trading_enabled": False,
    }
