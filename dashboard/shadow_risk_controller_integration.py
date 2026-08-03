
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_shadow_risk_controller_payload(root: Path) -> dict[str, Any]:
    path = (
        root
        / "release/v82_13_to_v82_16/actual/"
        / "shadow_risk_controller_dashboard_state.json"
    )
    if not path.exists():
        return {"risk_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"risk_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "risk_state": "NOT_AVAILABLE"
    }
