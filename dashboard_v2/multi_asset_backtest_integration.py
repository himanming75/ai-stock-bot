from __future__ import annotations

import json
from pathlib import Path


def build_multi_asset_backtest_payload(root: Path) -> dict:
    path = (
        root / "release/v87_17_to_v87_24/actual/"
        "multi_asset_backtest_result.json"
    )
    if not path.exists():
        return {"multi_asset_backtest_state": "NOT_AVAILABLE"}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"multi_asset_backtest_state": "NOT_AVAILABLE"}
    return value if isinstance(value, dict) else {
        "multi_asset_backtest_state": "NOT_AVAILABLE"
    }
