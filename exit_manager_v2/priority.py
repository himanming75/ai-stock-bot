from __future__ import annotations
from typing import Any

PRIORITY = {
    "KILL_SWITCH": 1,
    "RISK_EXIT": 2,
    "STOP_LOSS": 3,
    "TRAILING_STOP": 4,
    "BREAK_EVEN": 5,
    "TAKE_PROFIT": 6,
    "TIME_EXIT": 7,
}

def select(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    active = [c for c in candidates if c.get("triggered")]
    if not active:
        return {}
    active.sort(key=lambda c: PRIORITY.get(str(c.get("reason")), 999))
    return active[0]
