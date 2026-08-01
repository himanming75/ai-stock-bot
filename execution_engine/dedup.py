from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .models import OrderIntent


@dataclass
class DuplicateIntentGuard:
    ttl_seconds: int = 300
    _seen: dict[tuple[str, str, str, str], datetime] = None

    def __post_init__(self) -> None:
        if self.ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if self._seen is None:
            self._seen = {}

    def fingerprint(self, intent: OrderIntent) -> tuple[str, str, str, str]:
        return (
            intent.strategy_name,
            intent.symbol,
            intent.side.value,
            str(intent.quantity),
        )

    def is_duplicate(self, intent: OrderIntent) -> bool:
        key = self.fingerprint(intent)
        previous = self._seen.get(key)
        if previous is not None:
            age = (intent.created_at - previous).total_seconds()
            if 0 <= age < self.ttl_seconds:
                return True
        self._seen[key] = intent.created_at
        return False
