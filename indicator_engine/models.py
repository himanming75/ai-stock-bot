from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Bar:
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Bar":
        return cls(
            timestamp=str(value.get("timestamp", "")),
            open=float(value["open"]),
            high=float(value["high"]),
            low=float(value["low"]),
            close=float(value["close"]),
            volume=float(value.get("volume", 0)),
        )

    def validate(self) -> None:
        if self.high < self.low:
            raise ValueError("high must be greater than or equal to low")
        if not (self.low <= self.open <= self.high):
            raise ValueError("open must be inside high/low range")
        if not (self.low <= self.close <= self.high):
            raise ValueError("close must be inside high/low range")
        if self.volume < 0:
            raise ValueError("volume must not be negative")
