from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class StabilityAction(str, Enum):
    CYCLE_COMPLETED = "CYCLE_COMPLETED"
    CYCLE_FAILED = "CYCLE_FAILED"
    BACKOFF = "BACKOFF"
    RECOVERED = "RECOVERED"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"
    WATCHDOG_TIMEOUT = "WATCHDOG_TIMEOUT"
    SHUTDOWN = "SHUTDOWN"


class WatchdogStatus(str, Enum):
    HEALTHY = "HEALTHY"
    STALE = "STALE"
    STOPPED = "STOPPED"


@dataclass(frozen=True)
class StabilityResult:
    status: str
    action: StabilityAction
    cycle_number: int
    consecutive_failures: int
    backoff_seconds: float
    runtime_state: str
    detail: str

    def to_json_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["action"] = self.action.value
        return raw
