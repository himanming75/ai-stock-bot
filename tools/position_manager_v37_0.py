#!/usr/bin/env python3
"""
V37.0 Position Manager Foundation

Implements:
- Long and short position accounting
- Average entry price calculation
- Realized and unrealized P&L
- Cost basis and market value
- Partial close and full close
- Position flip handling
- Immutable position event ledger
- SHA-256 audit hashes
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


VERSION = "37.0"


class PositionSide(str, Enum):
    FLAT = "flat"
    LONG = "long"
    SHORT = "short"


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


def decimal_value(value: str, field_name: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not number.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return number


def positive_decimal(value: str, field_name: str) -> Decimal:
    number = decimal_value(value, field_name)
    if number <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return number


def normalize_decimal(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


@dataclass(frozen=True)
class PositionEvent:
    event_id: str
    position_id: str
    symbol: str
    generated_at: str
    event_type: str
    trade_side: str
    trade_quantity: str
    trade_price: str
    previous_side: str
    new_side: str
    previous_quantity: str
    new_quantity: str
    previous_average_price: str | None
    new_average_price: str | None
    realized_pnl_delta: str
    cumulative_realized_pnl: str
    event_sha256: str


@dataclass(frozen=True)
class PositionSnapshot:
    position_id: str
    symbol: str
    side: str
    quantity: str
    average_price: str | None
    market_price: str | None
    cost_basis: str
    market_value: str
    unrealized_pnl: str
    realized_pnl: str
    total_pnl: str
    event_count: int
    closed: bool
    generated_at: str
    snapshot_sha256: str


class PositionManagerError(RuntimeError):
    pass


class PositionManager:
    def __init__(self, symbol: str) -> None:
        symbol = symbol.strip().upper()
        if not symbol:
            raise ValueError("symbol is required")

        self.position_id = f"position-{uuid.uuid4().hex}"
        self.symbol = symbol
        self.side = PositionSide.FLAT
        self.quantity = Decimal("0")
        self.average_price: Decimal | None = None
        self.realized_pnl = Decimal("0")
        self.market_price: Decimal | None = None
        self._events: list[PositionEvent] = []

    def _record(
        self,
        *,
        event_type: str,
        trade_side: str,
        trade_quantity: Decimal,
        trade_price: Decimal,
        previous_side: PositionSide,
        previous_quantity: Decimal,
        previous_average_price: Decimal | None,
        realized_pnl_delta: Decimal,
    ) -> PositionEvent:
        core = {
            "event_id": f"evt-{uuid.uuid4().hex}",
            "position_id": self.position_id,
            "symbol": self.symbol,
            "generated_at": utc_now(),
            "event_type": event_type,
            "trade_side": trade_side,
            "trade_quantity": normalize_decimal(trade_quantity),
            "trade_price": normalize_decimal(trade_price),
            "previous_side": previous_side.value,
            "new_side": self.side.value,
            "previous_quantity": normalize_decimal(previous_quantity),
            "new_quantity": normalize_decimal(self.quantity),
            "previous_average_price": (
                normalize_decimal(previous_average_price)
                if previous_average_price is not None
                else None
            ),
            "new_average_price": (
                normalize_decimal(self.average_price)
                if self.average_price is not None
                else None
            ),
            "realized_pnl_delta": normalize_decimal(realized_pnl_delta),
            "cumulative_realized_pnl": normalize_decimal(self.realized_pnl),
        }
        event = PositionEvent(
            **core,
            event_sha256=canonical_hash(core),
        )
        self._events.append(event)
        return event

    def apply_fill(
        self,
        *,
        trade_side: str,
        quantity: str,
        price: str,
    ) -> PositionEvent:
        trade_side = trade_side.strip().lower()
        if trade_side not in {"buy", "sell"}:
            raise ValueError("trade_side must be buy or sell")

        trade_qty = positive_decimal(quantity, "quantity")
        trade_price = positive_decimal(price, "price")

        previous_side = self.side
        previous_quantity = self.quantity
        previous_average = self.average_price
        realized_delta = Decimal("0")

        if self.side == PositionSide.FLAT:
            if trade_side == "buy":
                self.side = PositionSide.LONG
            else:
                self.side = PositionSide.SHORT
            self.quantity = trade_qty
            self.average_price = trade_price
            event_type = "position_opened"

        elif self.side == PositionSide.LONG:
            if trade_side == "buy":
                total_cost = (
                    self.quantity * (self.average_price or Decimal("0"))
                    + trade_qty * trade_price
                )
                self.quantity += trade_qty
                self.average_price = total_cost / self.quantity
                event_type = "position_increased"
            else:
                if trade_qty < self.quantity:
                    realized_delta = (
                        trade_price - (self.average_price or Decimal("0"))
                    ) * trade_qty
                    self.quantity -= trade_qty
                    self.realized_pnl += realized_delta
                    event_type = "position_reduced"
                elif trade_qty == self.quantity:
                    realized_delta = (
                        trade_price - (self.average_price or Decimal("0"))
                    ) * trade_qty
                    self.realized_pnl += realized_delta
                    self.side = PositionSide.FLAT
                    self.quantity = Decimal("0")
                    self.average_price = None
                    event_type = "position_closed"
                else:
                    close_qty = self.quantity
                    excess = trade_qty - close_qty
                    realized_delta = (
                        trade_price - (self.average_price or Decimal("0"))
                    ) * close_qty
                    self.realized_pnl += realized_delta
                    self.side = PositionSide.SHORT
                    self.quantity = excess
                    self.average_price = trade_price
                    event_type = "position_flipped"

        elif self.side == PositionSide.SHORT:
            if trade_side == "sell":
                total_proceeds_basis = (
                    self.quantity * (self.average_price or Decimal("0"))
                    + trade_qty * trade_price
                )
                self.quantity += trade_qty
                self.average_price = total_proceeds_basis / self.quantity
                event_type = "position_increased"
            else:
                if trade_qty < self.quantity:
                    realized_delta = (
                        (self.average_price or Decimal("0")) - trade_price
                    ) * trade_qty
                    self.quantity -= trade_qty
                    self.realized_pnl += realized_delta
                    event_type = "position_reduced"
                elif trade_qty == self.quantity:
                    realized_delta = (
                        (self.average_price or Decimal("0")) - trade_price
                    ) * trade_qty
                    self.realized_pnl += realized_delta
                    self.side = PositionSide.FLAT
                    self.quantity = Decimal("0")
                    self.average_price = None
                    event_type = "position_closed"
                else:
                    close_qty = self.quantity
                    excess = trade_qty - close_qty
                    realized_delta = (
                        (self.average_price or Decimal("0")) - trade_price
                    ) * close_qty
                    self.realized_pnl += realized_delta
                    self.side = PositionSide.LONG
                    self.quantity = excess
                    self.average_price = trade_price
                    event_type = "position_flipped"

        return self._record(
            event_type=event_type,
            trade_side=trade_side,
            trade_quantity=trade_qty,
            trade_price=trade_price,
            previous_side=previous_side,
            previous_quantity=previous_quantity,
            previous_average_price=previous_average,
            realized_pnl_delta=realized_delta,
        )

    def mark_price(self, price: str) -> None:
        self.market_price = positive_decimal(price, "market_price")

    def cost_basis(self) -> Decimal:
        if self.side == PositionSide.FLAT or self.average_price is None:
            return Decimal("0")
        return self.quantity * self.average_price

    def market_value(self) -> Decimal:
        if self.side == PositionSide.FLAT or self.market_price is None:
            return Decimal("0")
        return self.quantity * self.market_price

    def unrealized_pnl(self) -> Decimal:
        if (
            self.side == PositionSide.FLAT
            or self.market_price is None
            or self.average_price is None
        ):
            return Decimal("0")

        if self.side == PositionSide.LONG:
            return (
                self.market_price - self.average_price
            ) * self.quantity

        return (
            self.average_price - self.market_price
        ) * self.quantity

    def total_pnl(self) -> Decimal:
        return self.realized_pnl + self.unrealized_pnl()

    def snapshot(self) -> PositionSnapshot:
        core = {
            "position_id": self.position_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": normalize_decimal(self.quantity),
            "average_price": (
                normalize_decimal(self.average_price)
                if self.average_price is not None
                else None
            ),
            "market_price": (
                normalize_decimal(self.market_price)
                if self.market_price is not None
                else None
            ),
            "cost_basis": normalize_decimal(self.cost_basis()),
            "market_value": normalize_decimal(self.market_value()),
            "unrealized_pnl": normalize_decimal(self.unrealized_pnl()),
            "realized_pnl": normalize_decimal(self.realized_pnl),
            "total_pnl": normalize_decimal(self.total_pnl()),
            "event_count": len(self._events),
            "closed": self.side == PositionSide.FLAT,
            "generated_at": utc_now(),
        }
        return PositionSnapshot(
            **core,
            snapshot_sha256=canonical_hash(core),
        )

    def ledger(self) -> list[PositionEvent]:
        return list(self._events)

    def export(self) -> dict[str, Any]:
        return {
            "schema_version": "v37.0.position_ledger.1",
            "version": VERSION,
            "snapshot": asdict(self.snapshot()),
            "events": [asdict(item) for item in self.ledger()],
            "network_used": False,
        }


def demo_position(
    *,
    symbol: str,
    first_quantity: str,
    first_price: str,
    second_quantity: str,
    second_price: str,
    sell_quantity: str,
    sell_price: str,
    market_price: str,
) -> dict[str, Any]:
    manager = PositionManager(symbol)
    manager.apply_fill(
        trade_side="buy",
        quantity=first_quantity,
        price=first_price,
    )
    manager.apply_fill(
        trade_side="buy",
        quantity=second_quantity,
        price=second_price,
    )
    manager.apply_fill(
        trade_side="sell",
        quantity=sell_quantity,
        price=sell_price,
    )
    manager.mark_price(market_price)
    return manager.export()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="V37.0 Position Manager Foundation"
    )
    p.add_argument("--symbol", default="AAPL")
    p.add_argument("--first-quantity", default="4")
    p.add_argument("--first-price", default="200")
    p.add_argument("--second-quantity", default="6")
    p.add_argument("--second-price", default="210")
    p.add_argument("--sell-quantity", default="3")
    p.add_argument("--sell-price", default="215")
    p.add_argument("--market-price", default="212")
    p.add_argument(
        "--output",
        default="release/v37/audit/position_manager_result_v37_0.json",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    payload = demo_position(
        symbol=args.symbol,
        first_quantity=args.first_quantity,
        first_price=args.first_price,
        second_quantity=args.second_quantity,
        second_price=args.second_price,
        sell_quantity=args.sell_quantity,
        sell_price=args.sell_price,
        market_price=args.market_price,
    )
    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
