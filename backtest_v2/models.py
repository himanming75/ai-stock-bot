from __future__ import annotations

from dataclasses import dataclass, asdict
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
            raise ValueError("high must be >= low")
        if not (self.low <= self.open <= self.high):
            raise ValueError("open must be within high/low")
        if not (self.low <= self.close <= self.high):
            raise ValueError("close must be within high/low")
        if self.volume < 0:
            raise ValueError("volume must be non-negative")


@dataclass
class Trade:
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    quantity: float
    side: str
    gross_pnl: float
    commission: float
    slippage_cost: float
    net_pnl: float
    return_pct: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
