from __future__ import annotations
from typing import Any

def detect_duplicate_sessions(
    sessions: list[dict[str, Any]],
    ledger_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    completed_keys={
        str(row.get("session_key"))
        for row in ledger_rows
        if row.get("state")=="COMPLETE"
    }
    duplicates=[
        row.get("session_id")
        for row in sessions
        if row.get("session_key") in completed_keys
    ]
    return {
        "duplicate_count":len(duplicates),
        "duplicate_session_ids":duplicates,
        "passed":not duplicates,
    }
