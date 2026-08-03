
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_end_of_day_payload(root: Path) -> dict[str, Any]:
    path = (
        root
        / "release/v82_33_to_v82_36/actual/"
        / "end_of_day_dashboard_state.json"
    )
    if not path.exists():
        return {"end_of_day_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"end_of_day_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "end_of_day_state": "NOT_AVAILABLE"
    }
