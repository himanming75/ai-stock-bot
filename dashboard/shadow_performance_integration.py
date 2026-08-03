
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_shadow_performance_payload(root: Path) -> dict[str, Any]:
    path = (
        root
        / "release/v82_09_to_v82_12/actual/"
        / "shadow_performance_dashboard_state.json"
    )
    if not path.exists():
        return {"analytics_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"analytics_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "analytics_state": "NOT_AVAILABLE"
    }
