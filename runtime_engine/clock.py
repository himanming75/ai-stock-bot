from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Return an aware UTC datetime."""


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


@dataclass
class ManualClock:
    current: datetime

    def __post_init__(self) -> None:
        if self.current.tzinfo is None:
            raise ValueError("ManualClock requires an aware datetime")
        self.current = self.current.astimezone(timezone.utc)

    def now(self) -> datetime:
        return self.current

    def advance(self, *, seconds: float = 0) -> datetime:
        self.current += timedelta(seconds=seconds)
        return self.current
