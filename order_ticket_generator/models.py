from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any


def D(value: Any, default: str = "0") -> Decimal:
    if value is None or value == "":
        return Decimal(default)
    return value if isinstance(value, Decimal) else Decimal(str(value))


@dataclass(frozen=True)
class TicketPolicy:
    time_in_force: str = "day"
    extended_hours: bool = False
    client_order_prefix: str = "aisb"
    minimum_quantity: Decimal = Decimal("0.0001")
    maximum_ticket_notional: Decimal = Decimal("5000")
    fractional_precision: int = 4

    @classmethod
    def from_mapping(cls, data: dict | None) -> "TicketPolicy":
        data = data or {}
        return cls(
            time_in_force=str(data.get("time_in_force", "day")),
            extended_hours=bool(data.get("extended_hours", False)),
            client_order_prefix=str(data.get("client_order_prefix", "aisb")),
            minimum_quantity=D(data.get("minimum_quantity"), "0.0001"),
            maximum_ticket_notional=D(data.get("maximum_ticket_notional"), "5000"),
            fractional_precision=int(data.get("fractional_precision", 4)),
        )


@dataclass(frozen=True)
class OrderTicket:
    ticket_id: str
    client_order_id: str
    parent_symbol: str
    slice_number: int
    slice_count: int
    payload: dict
    estimated_notional: Decimal
    idempotency_key: str
    blocked: bool
    blockers: tuple[str, ...]

    def as_json(self) -> dict:
        data = asdict(self)
        data["estimated_notional"] = str(self.estimated_notional)
        data["blockers"] = list(self.blockers)
        return data
