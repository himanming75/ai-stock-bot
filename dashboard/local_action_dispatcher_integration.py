
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_local_action_dispatcher_payload(root: Path) -> dict[str, Any]:
    path = (
        root
        / "release/v83_05_to_v83_08/actual/"
        / "local_action_dispatcher_dashboard_state.json"
    )
    if not path.exists():
        return {"dispatcher_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"dispatcher_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "dispatcher_state": "NOT_AVAILABLE"
    }
