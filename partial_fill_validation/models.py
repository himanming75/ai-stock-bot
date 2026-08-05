from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any


def D(value: Any, default: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


@dataclass(frozen=True)
class PartialFillState:
    order_id: str
    client_order_id: str
    symbol: str
    side: str
    status: str
    requested_qty: Decimal
    filled_qty: Decimal
    remaining_qty: Decimal
    filled_avg_price: Decimal | None
    filled_notional: Decimal
    fill_ratio: Decimal
    position_qty: Decimal
    position_consistent: bool
    blockers: tuple[str, ...]

    def as_json(self) -> dict:
        data = asdict(self)
        for key, value in list(data.items()):
            if isinstance(value, Decimal):
                data[key] = str(value)
            elif isinstance(value, tuple):
                data[key] = list(value)
        return data
