from __future__ import annotations
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class RecoveryStep:
    name: str
    action: str
    automatic: bool
    max_attempts: int
    backoff_seconds: tuple[int, ...]
    requires_operator: bool

    def to_dict(self) -> dict:
        value = asdict(self)
        value["backoff_seconds"] = list(self.backoff_seconds)
        return value


@dataclass(frozen=True)
class RecoveryDecision:
    trigger: str
    state: str
    read_allowed: bool
    write_allowed: bool
    next_action: str
    retry_after_seconds: int
    requires_operator: bool

    def to_dict(self) -> dict:
        return asdict(self)
