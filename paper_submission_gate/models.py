from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any


def D(value: Any, default: str = "0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    return value if isinstance(value, Decimal) else Decimal(str(value))


@dataclass(frozen=True)
class SubmissionPolicy:
    maximum_total_orders: int = 1
    maximum_order_notional: Decimal = Decimal("100")
    maximum_quantity: Decimal = Decimal("1")
    allowed_symbols: tuple[str, ...] = ("SPY", "QQQ", "IWM")
    require_market_open: bool = True
    require_limit_order: bool = True

    @classmethod
    def from_mapping(cls, data: dict | None) -> "SubmissionPolicy":
        data = data or {}
        return cls(
            maximum_total_orders=int(data.get("maximum_total_orders", 1)),
            maximum_order_notional=D(data.get("maximum_order_notional"), "100"),
            maximum_quantity=D(data.get("maximum_quantity"), "1"),
            allowed_symbols=tuple(
                str(x).upper() for x in data.get(
                    "allowed_symbols", ["SPY", "QQQ", "IWM"]
                )
            ),
            require_market_open=bool(data.get("require_market_open", True)),
            require_limit_order=bool(data.get("require_limit_order", True)),
        )


@dataclass(frozen=True)
class SubmissionRecord:
    ticket_id: str
    client_order_id: str
    symbol: str
    submitted: bool
    broker_order_id: str | None
    broker_status: str | None
    blocked: bool
    blockers: tuple[str, ...]
    broker_response: dict | None

    def as_json(self) -> dict:
        data = asdict(self)
        data["blockers"] = list(self.blockers)
        return data
