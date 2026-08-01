from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4


class SignalAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    timestamp: datetime
    last_price: Decimal
    bid_price: Decimal | None = None
    ask_price: Decimal | None = None
    recent_closes: tuple[Decimal, ...] = ()
    position_quantity: Decimal = Decimal("0")
    cash_available: Decimal = Decimal("0")
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("symbol must be uppercase")
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        if self.last_price <= 0:
            raise ValueError("last_price must be positive")
        if self.bid_price is not None and self.bid_price <= 0:
            raise ValueError("bid_price must be positive")
        if self.ask_price is not None and self.ask_price <= 0:
            raise ValueError("ask_price must be positive")
        if self.bid_price is not None and self.ask_price is not None and self.bid_price > self.ask_price:
            raise ValueError("crossed snapshot")
        if any(price <= 0 for price in self.recent_closes):
            raise ValueError("recent closes must be positive")


@dataclass(frozen=True)
class StrategySignal:
    strategy_name: str
    symbol: str
    action: SignalAction
    confidence: Decimal
    generated_at: datetime
    reason: str
    reference_price: Decimal
    suggested_quantity: Decimal = Decimal("0")
    signal_id: str = field(default_factory=lambda: uuid4().hex)
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.strategy_name:
            raise ValueError("strategy_name is required")
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("symbol must be uppercase")
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must be timezone-aware")
        if not Decimal("0") <= self.confidence <= Decimal("1"):
            raise ValueError("confidence must be between 0 and 1")
        if self.reference_price <= 0:
            raise ValueError("reference_price must be positive")
        if self.suggested_quantity < 0:
            raise ValueError("suggested_quantity cannot be negative")
        if self.action == SignalAction.HOLD and self.suggested_quantity != 0:
            raise ValueError("HOLD signal quantity must be zero")
