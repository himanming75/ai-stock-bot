from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    status: str
    blocking: bool
    evidence: str
    next_action: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ValidationGate:
    name: str
    status: str
    required_for_paper: bool
    required_for_live: bool
    blocking_reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
