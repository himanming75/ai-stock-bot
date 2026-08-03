from __future__ import annotations

import json
from pathlib import Path


def build_validation_v2_payload(root: Path) -> dict:
    path = (
        root / "release/v87_09_to_v87_16/actual/"
        "walk_forward_stress_validation_result.json"
    )
    if not path.exists():
        return {"walk_forward_stress_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"walk_forward_stress_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "walk_forward_stress_state": "NOT_AVAILABLE"
    }
