from __future__ import annotations
from datetime import date
from typing import Any

def select_session(
    scheduler: dict[str, Any],
    requested_date: str | None = None,
) -> dict[str, Any]:
    sessions = scheduler.get("queue", {}).get("sessions", [])
    if requested_date:
        matches = [
            row for row in sessions
            if str(row.get("session_date")) == requested_date
        ]
        if matches:
            return {
                "session_available": True,
                "session": matches[0],
                "selection_reason": "REQUESTED_DATE_MATCH",
            }
        return {
            "session_available": False,
            "session": None,
            "selection_reason": "REQUESTED_DATE_NOT_FOUND",
        }

    today = date.today().isoformat()
    eligible = [
        row for row in sessions
        if row.get("state") in {"QUEUED", "PREOPEN", "WAITING"}
    ]
    if not eligible:
        return {
            "session_available": False,
            "session": None,
            "selection_reason": "NO_ELIGIBLE_SESSION",
        }
    eligible.sort(key=lambda row: str(row.get("session_date", "")))
    selected = next(
        (row for row in eligible if row.get("session_date") >= today),
        eligible[0],
    )
    return {
        "session_available": True,
        "session": selected,
        "selection_reason": "EARLIEST_ELIGIBLE_SESSION",
    }
