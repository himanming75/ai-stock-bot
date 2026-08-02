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


def build_pilot_automation_payload(root: Path) -> dict[str, Any]:
    state = _load(
        root / "release/op4_17_to_op4_20/actual/"
        "paper_pilot_automation_dashboard_state.json"
    )
    return {
        "dashboard_stage": "OP4.17-OP4.20",
        "automation_state": state.get("automation_state", "NOT_AVAILABLE"),
        "pilot_id": state.get("pilot_id", ""),
        "session_id": state.get("session_id", ""),
        "cycle_ready": bool(state.get("cycle_ready", False)),
        "cycle_authorized": bool(state.get("cycle_authorized", False)),
        "snapshot_ready": bool(state.get("snapshot_ready", False)),
        "session_health": state.get("session_health", "NOT_AVAILABLE"),
        "emergency_stop_required": bool(
            state.get("emergency_stop_required", False)
        ),
        "recovery_gate_clear": bool(
            state.get("recovery_gate_clear", False)
        ),
        "recovery_reasons": (
            state.get("recovery_reasons", [])
            if isinstance(state.get("recovery_reasons"), list)
            else []
        ),
        "single_cycle_only": True,
        "continuous_loop_enabled": False,
        "paper_only": True,
        "broker_write_enabled": False,
        "live_trading_enabled": False,
    }
