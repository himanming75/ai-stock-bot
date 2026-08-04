from __future__ import annotations
from typing import Any

def select_next_session(scheduler: dict[str, Any]) -> dict[str, Any]:
    sessions = scheduler.get("queue", {}).get("sessions", [])
    candidates = [
        row for row in sessions
        if row.get("state") not in {"COMPLETE", "BLOCKED"}
    ]
    if not candidates:
        return {
            "session_available": False,
            "session": None,
            "reason": "NO_PENDING_SESSION",
        }
    candidates.sort(key=lambda row: str(row.get("session_date", "")))
    return {
        "session_available": True,
        "session": candidates[0],
        "reason": "EARLIEST_PENDING_SESSION",
    }
