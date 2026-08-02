from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_promotion_gate_payload(root: Path) -> dict[str, Any]:
    path = (
        root / "release/op5_13_to_op5_16/actual/"
        "promotion_dashboard_state.json"
    )
    if not path.exists():
        return {"promotion_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"promotion_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "promotion_state": "NOT_AVAILABLE"
    }
