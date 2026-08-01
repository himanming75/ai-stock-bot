from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class HeartbeatStatus(str, Enum):
    NEVER = "NEVER"
    HEALTHY = "HEALTHY"
    STALE = "STALE"


@dataclass
class HeartbeatMonitor:
    stale_after_seconds: float
    last_beat_at: datetime | None = None
    beat_count: int = 0

    def __post_init__(self) -> None:
        if self.stale_after_seconds <= 0:
            raise ValueError("stale_after_seconds must be positive")

    def beat(self, now: datetime) -> None:
        self.last_beat_at = now
        self.beat_count += 1

    def status(self, now: datetime) -> HeartbeatStatus:
        if self.last_beat_at is None:
            return HeartbeatStatus.NEVER
        age = (now - self.last_beat_at).total_seconds()
        return HeartbeatStatus.HEALTHY if age <= self.stale_after_seconds else HeartbeatStatus.STALE
