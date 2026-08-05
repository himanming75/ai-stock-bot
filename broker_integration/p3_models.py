from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


KNOWN_ORDER_STATES = {
    "new",
    "accepted",
    "pending_new",
    "partially_filled",
    "filled",
    "canceled",
    "pending_cancel",
    "replaced",
    "rejected",
    "expired",
    "suspended",
}


@dataclass(frozen=True)
class NormalizedOrder:
    id: str
    client_order_id: str
    symbol: str
    side: str
    status: str
    qty: Decimal
    filled_qty: Decimal
    filled_avg_price: Decimal | None
    submitted_at: str
    filled_at: str

    @property
    def status_known(self) -> bool:
        return self.status in KNOWN_ORDER_STATES

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "client_order_id": self.client_order_id,
            "symbol": self.symbol,
            "side": self.side,
            "status": self.status,
            "qty": str(self.qty),
            "filled_qty": str(self.filled_qty),
            "filled_avg_price": (
                str(self.filled_avg_price)
                if self.filled_avg_price is not None
                else None
            ),
            "submitted_at": self.submitted_at,
            "filled_at": self.filled_at,
            "status_known": self.status_known,
        }


def normalize_order(value: dict[str, Any]) -> NormalizedOrder:
    price = value.get("filled_avg_price")
    return NormalizedOrder(
        id=str(value.get("id", "")),
        client_order_id=str(value.get("client_order_id", "")),
        symbol=str(value.get("symbol", "")).upper(),
        side=str(value.get("side", "")).lower(),
        status=str(value.get("status", "")).lower(),
        qty=Decimal(str(value.get("qty", "0") or "0")),
        filled_qty=Decimal(str(value.get("filled_qty", "0") or "0")),
        filled_avg_price=(
            Decimal(str(price))
            if price not in {None, ""}
            else None
        ),
        submitted_at=str(value.get("submitted_at", "")),
        filled_at=str(value.get("filled_at", "")),
    )
