from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class AutonomousRuntimeState(str, Enum):
    CREATED = "CREATED"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    STOPPED = "STOPPED"


class AutonomousDecision(str, Enum):
    WAIT_MARKET_CLOSED = "WAIT_MARKET_CLOSED"
    WAIT_NO_SIGNAL = "WAIT_NO_SIGNAL"
    BLOCKED_READ_DISABLED = "BLOCKED_READ_DISABLED"
    BLOCKED_WRITE_DISABLED = "BLOCKED_WRITE_DISABLED"
    PREVIEW_ORDER = "PREVIEW_ORDER"
    SUBMIT_SINGLE_PAPER_ORDER = "SUBMIT_SINGLE_PAPER_ORDER"


@dataclass(frozen=True)
class AutonomousCycleResult:
    status: str
    decision: AutonomousDecision
    runtime_state: AutonomousRuntimeState
    symbol: str
    quantity: int
    estimated_notional: float
    read_requests_executed: int
    write_requests_executed: int
    actual_paper_orders_submitted: int
    live_orders_submitted: int
    detail: str

    def to_json_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["decision"] = self.decision.value
        raw["runtime_state"] = self.runtime_state.value
        return raw
