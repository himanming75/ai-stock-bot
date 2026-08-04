from __future__ import annotations
from typing import Any

ALLOWED = {
    "IDLE": {"WAITING", "RUNNING", "STOPPING"},
    "WAITING": {"RUNNING", "PAUSED", "STOPPING"},
    "RUNNING": {"WAITING", "PAUSED", "RECOVERING", "STOPPING"},
    "PAUSED": {"WAITING", "STOPPING"},
    "RECOVERING": {"WAITING", "STOPPING"},
    "STOPPING": {"STOPPED"},
    "STOPPED": set(),
}

def transition(current: str, target: str) -> dict[str, Any]:
    allowed = target in ALLOWED.get(current, set())
    return {
        "from_state": current,
        "to_state": target,
        "allowed": allowed,
        "state": target if allowed else current,
    }
