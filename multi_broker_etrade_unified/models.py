from __future__ import annotations
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class UnifiedPosition:
    symbol: str
    total_quantity: Decimal
    weighted_average_price: Decimal
    total_market_value: Decimal
    total_unrealized_pl: Decimal
    account_count: int
    account_breakdown: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for key in (
            "total_quantity",
            "weighted_average_price",
            "total_market_value",
            "total_unrealized_pl",
        ):
            value[key] = str(value[key])
        value["account_breakdown"] = list(
            self.account_breakdown
        )
        return value


@dataclass(frozen=True)
class UnifiedOrder:
    broker: str
    account_id: str
    order_id: str
    symbol: str
    side: str
    quantity: Decimal
    filled_quantity: Decimal
    status: str
    canonical_status: str
    open_order: bool

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["quantity"] = str(self.quantity)
        value["filled_quantity"] = str(
            self.filled_quantity
        )
        return value
