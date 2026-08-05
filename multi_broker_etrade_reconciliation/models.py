from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ChangeEvent:
    event_type: str
    severity: str
    entity_type: str
    entity_key: str
    account_id: str | None
    symbol: str | None
    previous: Any
    current: Any
    delta: Any
    message: str

    def to_dict(self) -> dict:
        return asdict(self)
