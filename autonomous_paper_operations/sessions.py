from __future__ import annotations
from datetime import date,timedelta
from typing import Any

def build_sessions(
    start_date: str,
    session_count: int,
) -> list[dict[str, Any]]:
    current=date.fromisoformat(start_date)
    sessions=[]
    while len(sessions)<session_count:
        if current.weekday()<5:
            sessions.append({
                "session_number":len(sessions)+1,
                "session_date":current.isoformat(),
                "state":"QUEUED",
            })
        current+=timedelta(days=1)
    return sessions
