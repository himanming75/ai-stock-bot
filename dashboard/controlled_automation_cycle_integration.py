
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_controlled_cycle_payload(root: Path) -> dict[str, Any]:
    path = (
        root
        / "release/v83_09_to_v83_12/actual/"
        / "controlled_automation_cycle_dashboard_state.json"
    )
    if not path.exists():
        return {"controlled_cycle_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"controlled_cycle_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "controlled_cycle_state": "NOT_AVAILABLE"
    }
