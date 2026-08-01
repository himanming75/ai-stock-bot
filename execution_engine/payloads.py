from __future__ import annotations

from .models import OrderIntent, OrderType


class AlpacaPaperPayloadBuilder:
    """Build Alpaca paper order payloads without performing HTTP requests."""

    def build(self, intent: OrderIntent, client_order_id: str) -> dict[str, object]:
        intent.validate()
        if not client_order_id:
            raise ValueError("client_order_id is required")

        payload: dict[str, object] = {
            "symbol": intent.symbol,
            "qty": str(intent.quantity),
            "side": intent.side.value.lower(),
            "type": intent.order_type.value.lower(),
            "time_in_force": intent.time_in_force.value.lower(),
            "client_order_id": client_order_id,
        }
        if intent.order_type == OrderType.LIMIT:
            payload["limit_price"] = str(intent.limit_price)
        return payload
