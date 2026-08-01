from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class FreshnessStatus(str, Enum):
    NEVER = "NEVER"
    FRESH = "FRESH"
    STALE = "STALE"
    FUTURE = "FUTURE"


@dataclass
class FreshnessMonitor:
    stale_after_seconds: float
    future_tolerance_seconds: float = 2.0

    def __post_init__(self):
        if self.stale_after_seconds <= 0:
            raise ValueError("stale_after_seconds must be positive")
        if self.future_tolerance_seconds < 0:
            raise ValueError("future_tolerance_seconds cannot be negative")

    def status(self, *, message_time: datetime | None, now: datetime) -> FreshnessStatus:
        if message_time is None:
            return FreshnessStatus.NEVER
        age = (now - message_time).total_seconds()
        if age < -self.future_tolerance_seconds:
            return FreshnessStatus.FUTURE
        return FreshnessStatus.FRESH if age <= self.stale_after_seconds else FreshnessStatus.STALE
