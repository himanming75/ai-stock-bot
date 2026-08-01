from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any


class MarketSessionPhase(str, Enum):
    CLOSED = "CLOSED"
    PRE_MARKET = "PRE_MARKET"
    REGULAR = "REGULAR"
    AFTER_HOURS = "AFTER_HOURS"
    HOLIDAY = "HOLIDAY"
    WEEKEND = "WEEKEND"


class SchedulerAction(str, Enum):
    WAIT = "WAIT"
    PREPARE = "PREPARE"
    START_SESSION = "START_SESSION"
    RUN_CYCLE = "RUN_CYCLE"
    CLOSE_SESSION = "CLOSE_SESSION"
    RECOVER_SESSION = "RECOVER_SESSION"
    SKIP_DAY = "SKIP_DAY"


@dataclass(frozen=True)
class SchedulerDecision:
    decided_at: datetime
    phase: MarketSessionPhase
    action: SchedulerAction
    reason: str
    session_date: date
    next_wakeup_seconds: int


@dataclass
class SchedulerState:
    schema_version: int = 1
    current_phase: MarketSessionPhase = MarketSessionPhase.CLOSED
    session_date: date | None = None
    session_active: bool = False
    session_prepared: bool = False
    session_closed: bool = False
    cycle_count: int = 0
    heartbeat_count: int = 0
    restart_count: int = 0
    last_action: SchedulerAction = SchedulerAction.WAIT
    last_transition_at: datetime | None = None

    def to_json_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["current_phase"] = self.current_phase.value
        raw["last_action"] = self.last_action.value
        raw["session_date"] = (
            self.session_date.isoformat() if self.session_date is not None else None
        )
        raw["last_transition_at"] = (
            self.last_transition_at.isoformat()
            if self.last_transition_at is not None else None
        )
        return raw

    @classmethod
    def from_json_dict(cls, raw: dict[str, Any]) -> "SchedulerState":
        return cls(
            schema_version=int(raw["schema_version"]),
            current_phase=MarketSessionPhase(str(raw["current_phase"])),
            session_date=(
                date.fromisoformat(str(raw["session_date"]))
                if raw.get("session_date") else None
            ),
            session_active=bool(raw["session_active"]),
            session_prepared=bool(raw["session_prepared"]),
            session_closed=bool(raw["session_closed"]),
            cycle_count=int(raw["cycle_count"]),
            heartbeat_count=int(raw["heartbeat_count"]),
            restart_count=int(raw["restart_count"]),
            last_action=SchedulerAction(str(raw["last_action"])),
            last_transition_at=(
                datetime.fromisoformat(str(raw["last_transition_at"]))
                if raw.get("last_transition_at") else None
            ),
        )
