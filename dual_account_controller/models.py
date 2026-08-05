from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ControllerState:
    active_profile: str
    profile_locked: bool
    global_kill_switch: bool
    account_kill_switches: dict[str, bool]
    last_transition_reason: str
    last_transition_status: str
    sequence: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ControllerCommandResult:
    command: str
    status: str
    allowed: bool
    previous_profile: str
    current_profile: str
    reason: str
    sequence: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
