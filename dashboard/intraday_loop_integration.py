
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_intraday_loop_payload(root: Path) -> dict[str, Any]:
    path = (
        root
        / "release/v82_29_to_v82_32/actual/"
        / "intraday_loop_dashboard_state.json"
    )
    if not path.exists():
        return {"loop_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"loop_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "loop_state": "NOT_AVAILABLE"
    }
