from __future__ import annotations
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class HealthSignal:
    name: str
    status: str
    score: int
    weight: int
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class RoutingDecision:
    mode: str
    read_allowed: bool
    write_allowed: bool
    reason: str
    recovery_required: bool

    def to_dict(self) -> dict:
        return asdict(self)
