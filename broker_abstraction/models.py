from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class UniversalAccount:
    broker: str
    environment: str
    account_id: str
    account_id_masked: str
    account_type: str
    account_mode: str
    status: str
    cash: float | None = None
    buying_power: float | None = None
    equity: float | None = None
    market_value: float | None = None
    currency: str = "USD"
    read_only: bool = True
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UniversalPosition:
    broker: str
    environment: str
    account_id: str
    symbol: str
    security_type: str
    side: str
    quantity: float
    average_price: float | None
    market_price: float | None
    market_value: float | None
    cost_basis: float | None
    unrealized_pl: float | None
    unrealized_pl_percent: float | None
    day_pl: float | None
    day_pl_percent: float | None
    currency: str = "USD"
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UniversalOrder:
    broker: str
    environment: str
    account_id: str
    order_id: str
    symbol: str
    security_type: str
    side: str
    order_type: str
    time_in_force: str
    status: str
    quantity: float
    filled_quantity: float
    limit_price: float | None
    stop_price: float | None
    average_fill_price: float | None
    submitted_at: str | None
    executed_at: str | None
    read_only: bool = True
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UniversalQuote:
    broker: str
    environment: str
    symbol: str
    security_type: str
    bid: float | None
    ask: float | None
    last: float | None
    open: float | None
    high: float | None
    low: float | None
    previous_close: float | None
    volume: float | None
    timestamp: str | None
    status: str
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
