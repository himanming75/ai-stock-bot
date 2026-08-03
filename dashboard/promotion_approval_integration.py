from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_promotion_approval_payload(root: Path) -> dict[str, Any]:
    path = (
        root / "release/op5_17_to_op5_20/actual/"
        "promotion_approval_dashboard_state.json"
    )
    if not path.exists():
        return {"approval_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"approval_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "approval_state": "NOT_AVAILABLE"
    }
