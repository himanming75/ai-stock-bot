from __future__ import annotations

import json
from pathlib import Path


def build_indicator_engine_payload(root: Path) -> dict:
    path = (
        root / "release/v86_09_to_v86_16/actual/"
        "indicator_engine_result.json"
    )
    if not path.exists():
        return {"indicator_engine_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"indicator_engine_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "indicator_engine_state": "NOT_AVAILABLE"
    }
