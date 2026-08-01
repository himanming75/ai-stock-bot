from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from .models import StrategySignal


@dataclass
class DuplicateSignalGuard:
    ttl_seconds: int = 300
    _seen: dict[tuple[str, str, str, str], object] = None

    def __post_init__(self) -> None:
        if self.ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if self._seen is None:
            self._seen = {}

    def fingerprint(self, signal: StrategySignal) -> tuple[str, str, str, str]:
        return (
            signal.strategy_name,
            signal.symbol,
            signal.action.value,
            str(signal.reference_price),
        )

    def is_duplicate(self, signal: StrategySignal) -> bool:
        key = self.fingerprint(signal)
        previous = self._seen.get(key)
        if previous is not None:
            age = (signal.generated_at - previous).total_seconds()
            if 0 <= age < self.ttl_seconds:
                return True
        self._seen[key] = signal.generated_at
        return False
