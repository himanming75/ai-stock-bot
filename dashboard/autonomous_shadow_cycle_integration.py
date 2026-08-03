from __future__ import annotations
import json
from pathlib import Path
from typing import Any

def build_autonomous_shadow_cycle_payload(root: Path) -> dict[str, Any]:
    path = root / "release/v82_01_to_v82_04/actual/autonomous_shadow_cycle_dashboard_state.json"
    if not path.exists():
        return {"cycle_state": "NOT_AVAILABLE"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"cycle_state": "NOT_AVAILABLE"}
    return data if isinstance(data, dict) else {"cycle_state": "NOT_AVAILABLE"}
