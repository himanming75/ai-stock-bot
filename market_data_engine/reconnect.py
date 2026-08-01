from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ExponentialBackoff:
    initial_seconds: float = 1.0
    multiplier: float = 2.0
    maximum_seconds: float = 30.0
    attempt: int = 0

    def __post_init__(self):
        if self.initial_seconds <= 0 or self.multiplier < 1 or self.maximum_seconds <= 0:
            raise ValueError("invalid backoff configuration")

    def next_delay(self) -> float:
        delay = min(self.initial_seconds * (self.multiplier ** self.attempt), self.maximum_seconds)
        self.attempt += 1
        return delay

    def reset(self) -> None:
        self.attempt = 0
