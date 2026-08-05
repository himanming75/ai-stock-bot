from __future__ import annotations
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class AccountSnapshot:
    broker: str
    account_id: str
    currency: str
    equity: Decimal
    cash: Decimal
    buying_power: Decimal
    status: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for key in ("equity", "cash", "buying_power"):
            value[key] = str(value[key])
        return value


@dataclass(frozen=True)
class PositionSnapshot:
    broker: str
    account_id: str
    symbol: str
    quantity: Decimal
    average_price: Decimal
    market_value: Decimal
    unrealized_pl: Decimal

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for key in ("quantity", "average_price", "market_value", "unrealized_pl"):
            value[key] = str(value[key])
        return value


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: str
    quantity: Decimal
    order_type: str
    time_in_force: str
    limit_price: Decimal | None = None
    client_order_id: str | None = None

    def validate(self) -> None:
        if self.side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.order_type not in {"MARKET", "LIMIT"}:
            raise ValueError("unsupported order type")
        if self.order_type == "LIMIT" and self.limit_price is None:
            raise ValueError("limit price required")


@dataclass(frozen=True)
class OrderSnapshot:
    broker: str
    account_id: str
    order_id: str
    symbol: str
    side: str
    quantity: Decimal
    filled_quantity: Decimal
    status: str

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["quantity"] = str(self.quantity)
        value["filled_quantity"] = str(self.filled_quantity)
        return value
