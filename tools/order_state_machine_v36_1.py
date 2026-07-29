#!/usr/bin/env python3
"""
V36.1 Order State Machine Foundation

Implements:
- Order lifecycle state machine
- Valid/invalid transition enforcement
- Immutable order event timeline
- Basic fill accumulation
- Cancel request state
- Deterministic audit hashes
- JSON CLI output

No broker network calls are performed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import Any, Sequence


VERSION = "36.1"


class OrderState(str, Enum):
    CREATED = "created"
    VALIDATED = "validated"
    ROUTED = "routed"
    ACCEPTED = "accepted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCEL_PENDING = "cancel_pending"
    CANCELED = "canceled"
    REJECTED = "rejected"


TERMINAL_STATES = {
    OrderState.FILLED,
    OrderState.CANCELED,
    OrderState.REJECTED,
}


ALLOWED_TRANSITIONS: dict[OrderState, set[OrderState]] = {
    OrderState.CREATED: {
        OrderState.VALIDATED,
        OrderState.REJECTED,
    },
    OrderState.VALIDATED: {
        OrderState.ROUTED,
        OrderState.REJECTED,
    },
    OrderState.ROUTED: {
        OrderState.ACCEPTED,
        OrderState.REJECTED,
    },
    OrderState.ACCEPTED: {
        OrderState.PARTIALLY_FILLED,
        OrderState.FILLED,
        OrderState.CANCEL_PENDING,
        OrderState.REJECTED,
    },
    OrderState.PARTIALLY_FILLED: {
        OrderState.PARTIALLY_FILLED,
        OrderState.FILLED,
        OrderState.CANCEL_PENDING,
    },
    OrderState.CANCEL_PENDING: {
        OrderState.CANCELED,
        OrderState.PARTIALLY_FILLED,
        OrderState.FILLED,
    },
    OrderState.FILLED: set(),
    OrderState.CANCELED: set(),
    OrderState.REJECTED: set(),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def positive_decimal(value: str, field_name: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return number


def normalize_decimal(value: Decimal) -> str:
    return format(value.normalize(), "f")


@dataclass(frozen=True)
class OrderEvent:
    event_id: str
    order_id: str
    generated_at: str
    previous_state: str
    new_state: str
    event_type: str
    message: str
    details: dict[str, Any]
    event_sha256: str


@dataclass(frozen=True)
class OrderSnapshot:
    order_id: str
    client_order_id: str
    symbol: str
    side: str
    quantity: str
    filled_quantity: str
    remaining_quantity: str
    average_fill_price: str | None
    state: str
    terminal: bool
    event_count: int
    generated_at: str


class OrderLifecycleError(RuntimeError):
    pass


class OrderLifecycle:
    def __init__(
        self,
        *,
        symbol: str,
        side: str,
        quantity: str,
        client_order_id: str | None = None,
    ) -> None:
        symbol = symbol.strip().upper()
        side = side.strip().lower()
        if not symbol:
            raise ValueError("symbol is required")
        if side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")

        self.order_id = f"order-{uuid.uuid4().hex}"
        self.client_order_id = (
            client_order_id.strip()
            if client_order_id
            else f"v36-{uuid.uuid4().hex[:20]}"
        )
        self.symbol = symbol
        self.side = side
        self.quantity = positive_decimal(quantity, "quantity")
        self.filled_quantity = Decimal("0")
        self.fill_notional = Decimal("0")
        self.state = OrderState.CREATED
        self._events: list[OrderEvent] = []
        self._record(
            previous=OrderState.CREATED,
            new=OrderState.CREATED,
            event_type="created",
            message="Order lifecycle created.",
            details={},
        )

    def _record(
        self,
        *,
        previous: OrderState,
        new: OrderState,
        event_type: str,
        message: str,
        details: dict[str, Any],
    ) -> OrderEvent:
        core = {
            "event_id": f"evt-{uuid.uuid4().hex}",
            "order_id": self.order_id,
            "generated_at": utc_now(),
            "previous_state": previous.value,
            "new_state": new.value,
            "event_type": event_type,
            "message": message,
            "details": details,
        }
        event = OrderEvent(
            **core,
            event_sha256=canonical_hash(core),
        )
        self._events.append(event)
        return event

    def transition(
        self,
        new_state: OrderState,
        *,
        event_type: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> OrderEvent:
        if new_state not in ALLOWED_TRANSITIONS[self.state]:
            raise OrderLifecycleError(
                f"Invalid transition: {self.state.value} -> {new_state.value}"
            )
        previous = self.state
        self.state = new_state
        return self._record(
            previous=previous,
            new=new_state,
            event_type=event_type,
            message=message,
            details=details or {},
        )

    def validate(self) -> OrderEvent:
        return self.transition(
            OrderState.VALIDATED,
            event_type="validated",
            message="Order validation passed.",
        )

    def route(self) -> OrderEvent:
        return self.transition(
            OrderState.ROUTED,
            event_type="routed",
            message="Order routed to broker adapter.",
        )

    def accept(self) -> OrderEvent:
        return self.transition(
            OrderState.ACCEPTED,
            event_type="accepted",
            message="Broker accepted the order.",
        )

    def reject(self, reason: str) -> OrderEvent:
        return self.transition(
            OrderState.REJECTED,
            event_type="rejected",
            message=reason,
            details={"reason": reason},
        )

    def request_cancel(self) -> OrderEvent:
        return self.transition(
            OrderState.CANCEL_PENDING,
            event_type="cancel_requested",
            message="Cancel request recorded.",
        )

    def confirm_cancel(self) -> OrderEvent:
        return self.transition(
            OrderState.CANCELED,
            event_type="canceled",
            message="Order cancellation confirmed.",
        )

    def apply_fill(self, quantity: str, price: str) -> OrderEvent:
        if self.state not in {
            OrderState.ACCEPTED,
            OrderState.PARTIALLY_FILLED,
            OrderState.CANCEL_PENDING,
        }:
            raise OrderLifecycleError(
                f"Fill not allowed in {self.state.value} state"
            )

        fill_qty = positive_decimal(quantity, "fill quantity")
        fill_price = positive_decimal(price, "fill price")
        remaining = self.quantity - self.filled_quantity

        if fill_qty > remaining:
            raise OrderLifecycleError(
                "Fill quantity exceeds remaining order quantity"
            )

        self.filled_quantity += fill_qty
        self.fill_notional += fill_qty * fill_price

        if self.filled_quantity == self.quantity:
            new_state = OrderState.FILLED
            event_type = "filled"
            message = "Order fully filled."
        else:
            new_state = OrderState.PARTIALLY_FILLED
            event_type = "partial_fill"
            message = "Order partially filled."

        return self.transition(
            new_state,
            event_type=event_type,
            message=message,
            details={
                "fill_quantity": normalize_decimal(fill_qty),
                "fill_price": normalize_decimal(fill_price),
                "cumulative_filled_quantity": normalize_decimal(
                    self.filled_quantity
                ),
                "remaining_quantity": normalize_decimal(
                    self.quantity - self.filled_quantity
                ),
            },
        )

    def average_fill_price(self) -> str | None:
        if self.filled_quantity == 0:
            return None
        return normalize_decimal(
            self.fill_notional / self.filled_quantity
        )

    def snapshot(self) -> OrderSnapshot:
        return OrderSnapshot(
            order_id=self.order_id,
            client_order_id=self.client_order_id,
            symbol=self.symbol,
            side=self.side,
            quantity=normalize_decimal(self.quantity),
            filled_quantity=normalize_decimal(self.filled_quantity),
            remaining_quantity=normalize_decimal(
                self.quantity - self.filled_quantity
            ),
            average_fill_price=self.average_fill_price(),
            state=self.state.value,
            terminal=self.state in TERMINAL_STATES,
            event_count=len(self._events),
            generated_at=utc_now(),
        )

    def timeline(self) -> list[OrderEvent]:
        return list(self._events)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def demo_lifecycle(
    *,
    symbol: str,
    side: str,
    quantity: str,
    fill_quantity: str,
    fill_price: str,
) -> dict[str, Any]:
    order = OrderLifecycle(
        symbol=symbol,
        side=side,
        quantity=quantity,
    )
    order.validate()
    order.route()
    order.accept()
    order.apply_fill(fill_quantity, fill_price)

    return {
        "schema_version": "v36.1.order_lifecycle_demo.1",
        "version": VERSION,
        "snapshot": asdict(order.snapshot()),
        "timeline": [asdict(event) for event in order.timeline()],
        "network_used": False,
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="V36.1 Order State Machine Foundation"
    )
    p.add_argument("--symbol", default="AAPL")
    p.add_argument("--side", choices=["buy", "sell"], default="buy")
    p.add_argument("--quantity", default="10")
    p.add_argument("--fill-quantity", default="4")
    p.add_argument("--fill-price", default="200")
    p.add_argument(
        "--output",
        default="release/v36/audit/order_lifecycle_result_v36_1.json",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    payload = demo_lifecycle(
        symbol=args.symbol,
        side=args.side,
        quantity=args.quantity,
        fill_quantity=args.fill_quantity,
        fill_price=args.fill_price,
    )
    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
