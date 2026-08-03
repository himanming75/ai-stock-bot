
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_shadow_scheduler_payload(root: Path) -> dict[str, Any]:
    path = (
        root
        / "release/v82_05_to_v82_08/actual/"
        / "shadow_scheduler_dashboard_state.json"
    )
    if not path.exists():
        return {"scheduler_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"scheduler_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "scheduler_state": "NOT_AVAILABLE"
    }
