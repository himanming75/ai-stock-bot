from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class MarketPriceBook:
    prices: dict[str, Decimal] = None

    def __post_init__(self) -> None:
        if self.prices is None:
            self.prices = {}

    def update(self, symbol: str, price: Decimal) -> None:
        if not symbol or symbol != symbol.upper():
            raise ValueError("symbol must be uppercase")
        if price <= 0:
            raise ValueError("price must be positive")
        self.prices[symbol] = price

    def get(self, symbol: str, fallback: Decimal | None = None) -> Decimal:
        if symbol in self.prices:
            return self.prices[symbol]
        if fallback is not None:
            return fallback
        raise KeyError(symbol)
