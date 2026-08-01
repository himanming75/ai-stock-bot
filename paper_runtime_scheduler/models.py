from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class IntegrationEventType(str, Enum):
    PREPARED = "PREPARED"
    SESSION_STARTED = "SESSION_STARTED"
    CYCLE_COMPLETED = "CYCLE_COMPLETED"
    SESSION_RECOVERED = "SESSION_RECOVERED"
    SESSION_CLOSED = "SESSION_CLOSED"
    WAITING = "WAITING"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class IntegrationEvent:
    created_at: datetime
    event_type: IntegrationEventType
    scheduler_action: str
    runtime_state: str
    detail: str

    def to_json_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["created_at"] = self.created_at.isoformat()
        raw["event_type"] = self.event_type.value
        return raw


@dataclass(frozen=True)
class IntegrationResult:
    status: str
    scheduler_action: str
    event_type: IntegrationEventType
    runtime_state: str
    cycle_completed: bool
    recovery_saved: bool
    detail: str

    def to_json_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["event_type"] = self.event_type.value
        return raw
