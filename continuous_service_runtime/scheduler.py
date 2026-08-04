from __future__ import annotations
from typing import Any

def scheduler_tick(core_result: dict[str, Any]) -> dict[str, Any]:
    state = core_result.get("state")
    selected = core_result.get("selected_session", {}).get("session") or {}
    if state == "CONTINUOUS_AUTONOMOUS_ENGINE_WAITING_FOR_MANUAL_APPROVAL":
        action = "WAIT_FOR_MANUAL_APPROVAL"
    elif state == "CONTINUOUS_AUTONOMOUS_ENGINE_HOLD":
        action = "IDLE"
    elif selected:
        action = "PROCESS_SELECTED_SESSION"
    else:
        action = "WAIT_FOR_SESSION"
    return {
        "action": action,
        "selected_session_id": selected.get("session_id"),
        "selected_session_date": selected.get("session_date"),
        "core_state": state,
    }
