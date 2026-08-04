from __future__ import annotations
from typing import Any
from multi_day_scheduler.io import digest

SESSION_STATES=[
    "QUEUED","PREOPEN","MARKET_OPEN","INTRADAY",
    "MARKET_CLOSE","AFTER_HOURS","COMPLETE"
]

def build_session(day: str, source_cycle_id: str) -> dict[str, Any]:
    base={"session_date":day,"source_cycle_id":source_cycle_id}
    return {
        "session_id":digest(base)[:24],
        "session_key":digest({"kind":"SESSION",**base}),
        "session_date":day,
        "source_cycle_id":source_cycle_id,
        "state":"QUEUED",
        "current_phase":"QUEUED",
        "completed_phases":[],
        "attempt_count":0,
        "actual_orders_submitted":0,
        "execution_authorized":False,
        "paper_only":True,
    }

def advance_session(session: dict[str, Any]) -> dict[str, Any]:
    item=dict(session)
    current=item.get("current_phase","QUEUED")
    try:
        index=SESSION_STATES.index(current)
    except ValueError:
        index=0
    if index < len(SESSION_STATES)-1:
        completed=list(item.get("completed_phases",[]))
        completed.append(current)
        item["completed_phases"]=completed
        item["current_phase"]=SESSION_STATES[index+1]
        item["state"]=SESSION_STATES[index+1]
    return item
