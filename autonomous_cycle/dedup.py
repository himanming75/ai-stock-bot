from __future__ import annotations
from typing import Any

FINAL_STATES = {
    "AUTONOMOUS_CYCLE_COMPLETED",
    "AUTONOMOUS_CYCLE_WAITING_FOR_MANUAL_APPROVAL",
    "AUTONOMOUS_CYCLE_HOLD",
    "AUTONOMOUS_CYCLE_BLOCKED",
}

def detect_duplicate(
    cycle_key: str,
    ledger_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    matches = [
        row for row in ledger_rows
        if row.get("cycle_key") == cycle_key
        and row.get("state") in FINAL_STATES
    ]
    return {
        "duplicate_cycle": bool(matches),
        "duplicate_match_count": len(matches),
        "previous_cycle_id": (
            matches[-1].get("cycle_id") if matches else None
        ),
        "previous_state": (
            matches[-1].get("state") if matches else None
        ),
    }
