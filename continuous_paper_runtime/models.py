from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class ContinuousRuntimeState(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    RECOVERING = "RECOVERING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class ContinuousRuntimeAction(str, Enum):
    STARTED = "STARTED"
    TICK_COMPLETED = "TICK_COMPLETED"
    WAITED = "WAITED"
    SKIPPED = "SKIPPED"
    RECOVERED = "RECOVERED"
    SESSION_CLOSED = "SESSION_CLOSED"
    STOP_REQUESTED = "STOP_REQUESTED"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ContinuousRuntimeResult:
    status: str
    action: ContinuousRuntimeAction
    state: ContinuousRuntimeState
    tick_number: int
    cycles_completed: int
    detail: str

    def to_json_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["action"] = self.action.value
        raw["state"] = self.state.value
        return raw
