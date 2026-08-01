from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from threading import Lock


@dataclass
class ClientOrderIdGenerator:
    prefix: str = "BOT"
    _counter: int = 0

    def __post_init__(self) -> None:
        if not self.prefix or not self.prefix.replace("-", "").isalnum():
            raise ValueError("invalid prefix")
        self._lock = Lock()

    def next_id(self, now: datetime) -> str:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        with self._lock:
            self._counter += 1
            counter = self._counter
        return f"{self.prefix}-{now.strftime('%Y%m%d')}-{counter:06d}"
