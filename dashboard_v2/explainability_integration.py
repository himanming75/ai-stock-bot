from __future__ import annotations

import json
from pathlib import Path


def build_explainability_payload(root: Path) -> dict:
    path = (
        root / "release/v86_25_to_v86_32/actual/"
        "ai_explainability_result.json"
    )
    if not path.exists():
        return {"ai_explainability_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"ai_explainability_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "ai_explainability_state": "NOT_AVAILABLE"
    }
