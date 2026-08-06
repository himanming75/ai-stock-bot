from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceHealth:
    broker: str
    source_path: str
    available: bool
    generated_at: str | None
    age_seconds: float | None
    freshness: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReconciliationIssue:
    issue_type: str
    severity: str
    symbol: str | None
    account_id: str | None
    broker_left: str
    broker_right: str
    left_value: Any
    right_value: Any
    difference: float | None
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
