from __future__ import annotations

import json
from pathlib import Path


def build_backtest_v2_payload(root: Path) -> dict:
    path = (
        root / "release/v87_01_to_v87_08/actual/"
        "backtest_v2_result.json"
    )
    if not path.exists():
        return {"backtest_v2_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"backtest_v2_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "backtest_v2_state": "NOT_AVAILABLE"
    }
