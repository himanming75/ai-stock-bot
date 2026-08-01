from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class BrokerResponse:
    status_code: int
    payload: Any
    request_id: str | None
    attempts: int


@dataclass(frozen=True)
class BrokerAccount:
    account_id: str
    status: str
    cash: Decimal
    equity: Decimal
    buying_power: Decimal
    trading_blocked: bool


@dataclass(frozen=True)
class BrokerClock:
    timestamp: datetime
    is_open: bool
    next_open: datetime
    next_close: datetime


@dataclass(frozen=True)
class BrokerPosition:
    symbol: str
    quantity: Decimal
    average_entry_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal


@dataclass(frozen=True)
class BrokerOrder:
    order_id: str
    client_order_id: str
    symbol: str
    side: str
    quantity: Decimal
    filled_quantity: Decimal
    status: str


@dataclass(frozen=True)
class ReconciliationSummary:
    matched: bool
    cash_difference: Decimal
    equity_difference: Decimal
    missing_internal_symbols: tuple[str, ...]
    missing_broker_symbols: tuple[str, ...]
    quantity_mismatches: dict[str, dict[str, str]]
