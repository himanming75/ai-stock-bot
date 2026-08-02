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


def build_multi_day_validation_payload(
    root: Path,
) -> dict[str, Any]:
    state = _load(
        root / "release/op5_01_to_op5_04/actual/"
        "multi_day_validation_dashboard_state.json"
    )
    return {
        "dashboard_stage": "OP5.01-OP5.04",
        "validation_state": state.get(
            "validation_state", "NOT_AVAILABLE"
        ),
        "pilot_id": state.get("pilot_id", ""),
        "session_id": state.get("session_id", ""),
        "validation_days": int(
            state.get("validation_days", 0) or 0
        ),
        "healthy_days": int(
            state.get("healthy_days", 0) or 0
        ),
        "unhealthy_days": int(
            state.get("unhealthy_days", 0) or 0
        ),
        "consecutive_healthy_days": int(
            state.get("consecutive_healthy_days", 0) or 0
        ),
        "validation_complete": bool(
            state.get("validation_complete", False)
        ),
        "day_healthy": bool(
            state.get("day_healthy", False)
        ),
        "gate_reasons": (
            state.get("gate_reasons", [])
            if isinstance(state.get("gate_reasons"), list)
            else []
        ),
        "paper_only": True,
        "broker_write_enabled": False,
        "live_trading_enabled": False,
    }
