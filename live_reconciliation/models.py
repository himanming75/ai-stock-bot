from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class OrderState:
    broker_order_id: str
    client_order_id: str
    symbol: str
    side: str
    status: str
    filled_qty: Decimal
    filled_avg_price: Decimal | None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "OrderState":
        return cls(
            broker_order_id=str(value.get("id", "")),
            client_order_id=str(value.get("client_order_id", "")),
            symbol=str(value.get("symbol", "")).upper(),
            side=str(value.get("side", "")).lower(),
            status=str(value.get("status", "")).lower(),
            filled_qty=Decimal(str(value.get("filled_qty", "0"))),
            filled_avg_price=(
                Decimal(str(value["filled_avg_price"]))
                if value.get("filled_avg_price") not in {None, ""}
                else None
            ),
        )


@dataclass(frozen=True)
class PositionState:
    symbol: str
    qty: Decimal
    avg_entry_price: Decimal
    market_value: Decimal

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PositionState":
        return cls(
            symbol=str(value.get("symbol", "")).upper(),
            qty=Decimal(str(value.get("qty", "0"))),
            avg_entry_price=Decimal(str(value.get("avg_entry_price", "0"))),
            market_value=Decimal(str(value.get("market_value", "0"))),
        )
