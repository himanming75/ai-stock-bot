from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import uuid4


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class TimeInForce(str, Enum):
    DAY = "DAY"
    GTC = "GTC"


@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    side: OrderSide
    quantity: Decimal
    reference_price: Decimal
    estimated_notional: Decimal
    created_at: datetime
    expires_at: datetime
    source_signal_id: str
    strategy_name: str
    order_type: OrderType = OrderType.MARKET
    time_in_force: TimeInForce = TimeInForce.DAY
    limit_price: Decimal | None = None
    intent_id: str = field(default_factory=lambda: uuid4().hex)
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.symbol or self.symbol != self.symbol.upper():
            raise ValueError("symbol must be uppercase")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.reference_price <= 0:
            raise ValueError("reference_price must be positive")
        if self.estimated_notional <= 0:
            raise ValueError("estimated_notional must be positive")
        if self.created_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be after created_at")
        if not self.source_signal_id:
            raise ValueError("source_signal_id is required")
        if not self.strategy_name:
            raise ValueError("strategy_name is required")
        if self.order_type == OrderType.LIMIT and self.limit_price is None:
            raise ValueError("limit order requires limit_price")
        if self.order_type == OrderType.MARKET and self.limit_price is not None:
            raise ValueError("market order cannot include limit_price")
