from __future__ import annotations

import json
from pathlib import Path


def build_strategy_v2_payload(root: Path) -> dict:
    path = (
        root / "release/v86_01_to_v86_08/actual/"
        "strategy_engine_v2_result.json"
    )
    if not path.exists():
        return {"strategy_engine_v2_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"strategy_engine_v2_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "strategy_engine_v2_state": "NOT_AVAILABLE"
    }
