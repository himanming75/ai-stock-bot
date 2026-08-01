from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Position:
    symbol: str
    quantity: Decimal = Decimal("0")
    average_price: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")

    def validate(self) -> None:
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("symbol must be uppercase")
        if self.quantity < 0:
            raise ValueError("short positions are not supported")
        if self.average_price < 0:
            raise ValueError("average_price cannot be negative")

    def apply_buy(self, quantity: Decimal, price: Decimal) -> None:
        if quantity <= 0 or price <= 0:
            raise ValueError("buy values must be positive")
        total_cost = self.quantity * self.average_price + quantity * price
        self.quantity += quantity
        self.average_price = total_cost / self.quantity

    def apply_sell(self, quantity: Decimal, price: Decimal) -> Decimal:
        if quantity <= 0 or price <= 0:
            raise ValueError("sell values must be positive")
        if quantity > self.quantity:
            raise ValueError("insufficient position")
        pnl = quantity * (price - self.average_price)
        self.quantity -= quantity
        self.realized_pnl += pnl
        if self.quantity == 0:
            self.average_price = Decimal("0")
        return pnl


@dataclass(frozen=True)
class PositionSnapshot:
    symbol: str
    quantity: Decimal
    average_price: Decimal
    market_price: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal


@dataclass(frozen=True)
class PortfolioSnapshot:
    captured_at: datetime
    cash: Decimal
    equity: Decimal
    market_value: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    buying_power: Decimal
    positions: tuple[PositionSnapshot, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Portfolio:
    starting_cash: Decimal
    cash: Decimal | None = None
    positions: dict[str, Position] = field(default_factory=dict)
    realized_pnl: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if self.starting_cash <= 0:
            raise ValueError("starting_cash must be positive")
        if self.cash is None:
            self.cash = self.starting_cash
        if self.cash < 0:
            raise ValueError("cash cannot be negative")

    def get_position(self, symbol: str) -> Position:
        symbol = symbol.upper()
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol)
        return self.positions[symbol]
