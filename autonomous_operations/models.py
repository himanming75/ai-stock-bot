from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ModuleHealth:
    name: str
    status: str
    consecutive_failures: int
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CycleResult:
    cycle_id: str
    status: str
    final_action: str
    completed_modules: tuple[str, ...]
    blocked_module: str | None
    emergency_stop: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["completed_modules"] = list(self.completed_modules)
        return value
