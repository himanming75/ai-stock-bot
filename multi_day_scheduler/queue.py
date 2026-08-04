from __future__ import annotations
from typing import Any
from multi_day_scheduler.session import build_session

def build_queue(
    trading_days: list[str],
    source_cycle_id: str,
    previous_queue: dict[str, Any] | None = None,
) -> dict[str, Any]:
    previous_queue=previous_queue or {}
    previous={
        str(row.get("session_date")):row
        for row in previous_queue.get("sessions",[])
        if row.get("session_date")
    }
    sessions=[]
    for day in trading_days:
        if day in previous:
            sessions.append(previous[day])
        else:
            sessions.append(build_session(day,source_cycle_id))
    return {
        "source_cycle_id":source_cycle_id,
        "session_count":len(sessions),
        "sessions":sessions,
    }

def queue_summary(queue: dict[str, Any]) -> dict[str, Any]:
    sessions=queue.get("sessions",[])
    counts={}
    for row in sessions:
        state=str(row.get("state","UNKNOWN"))
        counts[state]=counts.get(state,0)+1
    return {
        "session_count":len(sessions),
        "state_counts":counts,
        "queued_count":sum(
            1 for row in sessions if row.get("state")=="QUEUED"
        ),
        "complete_count":sum(
            1 for row in sessions if row.get("state")=="COMPLETE"
        ),
    }
