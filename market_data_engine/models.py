from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal, TypeAlias


@dataclass(frozen=True)
class Quote:
    symbol: str
    timestamp: datetime
    bid_price: Decimal
    bid_size: int
    ask_price: Decimal
    ask_size: int
    sequence: int | None = None

    @property
    def midpoint(self) -> Decimal:
        return (self.bid_price + self.ask_price) / Decimal("2")


@dataclass(frozen=True)
class Trade:
    symbol: str
    timestamp: datetime
    price: Decimal
    size: int
    exchange: str | None = None
    sequence: int | None = None


@dataclass(frozen=True)
class Bar:
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    trade_count: int | None = None
    vwap: Decimal | None = None
    sequence: int | None = None


MarketDataMessage: TypeAlias = Quote | Trade | Bar
MarketDataKind: TypeAlias = Literal["quote", "trade", "bar"]
