#!/usr/bin/env python3
"""
V36.2 Partial Fill Engine

Builds on V36.1 order lifecycle concepts and adds:
- Multiple partial fills
- VWAP / cumulative average fill price
- Unique trade ID enforcement
- Duplicate fill detection
- Replay protection using immutable fill fingerprints
- Fill ledger and execution receipts
- Overfill prevention
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
from pathlib import Path
from typing import Any, Sequence


VERSION = "36.2"


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
class FillRecord:
    fill_id: str
    trade_id: str
    order_id: str
    symbol: str
    side: str
    quantity: str
    price: str
    notional: str
    cumulative_quantity: str
    remaining_quantity: str
    cumulative_vwap: str
    generated_at: str
    fill_sha256: str


@dataclass(frozen=True)
class FillReceipt:
    schema_version: str
    version: str
    order_id: str
    status: str
    accepted_trade_id: str | None
    duplicate: bool
    rejection_reason: str | None
    ledger_size: int
    cumulative_quantity: str
    remaining_quantity: str
    cumulative_vwap: str | None
    generated_at: str
    receipt_sha256: str


@dataclass(frozen=True)
class LedgerSnapshot:
    order_id: str
    symbol: str
    side: str
    order_quantity: str
    cumulative_quantity: str
    remaining_quantity: str
    cumulative_notional: str
    cumulative_vwap: str | None
    fill_count: int
    complete: bool
    generated_at: str


class FillEngineError(RuntimeError):
    pass


class PartialFillEngine:
    def __init__(
        self,
        *,
        order_id: str,
        symbol: str,
        side: str,
        order_quantity: str,
    ) -> None:
        symbol = symbol.strip().upper()
        side = side.strip().lower()

        if not order_id.strip():
            raise ValueError("order_id is required")
        if not symbol:
            raise ValueError("symbol is required")
        if side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")

        self.order_id = order_id.strip()
        self.symbol = symbol
        self.side = side
        self.order_quantity = positive_decimal(
            order_quantity,
            "order_quantity",
        )
        self.cumulative_quantity = Decimal("0")
        self.cumulative_notional = Decimal("0")
        self._fills: list[FillRecord] = []
        self._trade_ids: set[str] = set()
        self._fill_fingerprints: set[str] = set()

    def _fingerprint(
        self,
        *,
        trade_id: str,
        quantity: Decimal,
        price: Decimal,
    ) -> str:
        payload = {
            "order_id": self.order_id,
            "trade_id": trade_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": normalize_decimal(quantity),
            "price": normalize_decimal(price),
        }
        return canonical_hash(payload)

    def _receipt(
        self,
        *,
        status: str,
        accepted_trade_id: str | None,
        duplicate: bool,
        rejection_reason: str | None,
    ) -> FillReceipt:
        vwap = self.vwap()
        core = {
            "schema_version": "v36.2.fill_receipt.1",
            "version": VERSION,
            "order_id": self.order_id,
            "status": status,
            "accepted_trade_id": accepted_trade_id,
            "duplicate": duplicate,
            "rejection_reason": rejection_reason,
            "ledger_size": len(self._fills),
            "cumulative_quantity": normalize_decimal(
                self.cumulative_quantity
            ),
            "remaining_quantity": normalize_decimal(
                self.order_quantity - self.cumulative_quantity
            ),
            "cumulative_vwap": vwap,
            "generated_at": utc_now(),
        }
        return FillReceipt(
            **core,
            receipt_sha256=canonical_hash(core),
        )

    def apply_fill(
        self,
        *,
        trade_id: str,
        quantity: str,
        price: str,
    ) -> FillReceipt:
        trade_id = trade_id.strip()
        if not trade_id:
            raise ValueError("trade_id is required")

        fill_qty = positive_decimal(quantity, "fill quantity")
        fill_price = positive_decimal(price, "fill price")

        fingerprint = self._fingerprint(
            trade_id=trade_id,
            quantity=fill_qty,
            price=fill_price,
        )

        if trade_id in self._trade_ids:
            return self._receipt(
                status="REJECTED_DUPLICATE_TRADE_ID",
                accepted_trade_id=None,
                duplicate=True,
                rejection_reason="trade_id already exists",
            )

        if fingerprint in self._fill_fingerprints:
            return self._receipt(
                status="REJECTED_REPLAY",
                accepted_trade_id=None,
                duplicate=True,
                rejection_reason="fill replay fingerprint already exists",
            )

        remaining_before = (
            self.order_quantity - self.cumulative_quantity
        )
        if fill_qty > remaining_before:
            return self._receipt(
                status="REJECTED_OVERFILL",
                accepted_trade_id=None,
                duplicate=False,
                rejection_reason=(
                    "fill quantity exceeds remaining order quantity"
                ),
            )

        fill_notional = fill_qty * fill_price
        self.cumulative_quantity += fill_qty
        self.cumulative_notional += fill_notional

        cumulative_vwap = self.cumulative_notional / self.cumulative_quantity
        remaining_after = (
            self.order_quantity - self.cumulative_quantity
        )

        core = {
            "fill_id": f"fill-{uuid.uuid4().hex}",
            "trade_id": trade_id,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": normalize_decimal(fill_qty),
            "price": normalize_decimal(fill_price),
            "notional": normalize_decimal(fill_notional),
            "cumulative_quantity": normalize_decimal(
                self.cumulative_quantity
            ),
            "remaining_quantity": normalize_decimal(remaining_after),
            "cumulative_vwap": normalize_decimal(cumulative_vwap),
            "generated_at": utc_now(),
        }
        record = FillRecord(
            **core,
            fill_sha256=canonical_hash(core),
        )

        self._fills.append(record)
        self._trade_ids.add(trade_id)
        self._fill_fingerprints.add(fingerprint)

        status = (
            "FILLED"
            if self.cumulative_quantity == self.order_quantity
            else "PARTIALLY_FILLED"
        )
        return self._receipt(
            status=status,
            accepted_trade_id=trade_id,
            duplicate=False,
            rejection_reason=None,
        )

    def vwap(self) -> str | None:
        if self.cumulative_quantity == 0:
            return None
        return normalize_decimal(
            self.cumulative_notional / self.cumulative_quantity
        )

    def ledger(self) -> list[FillRecord]:
        return list(self._fills)

    def snapshot(self) -> LedgerSnapshot:
        return LedgerSnapshot(
            order_id=self.order_id,
            symbol=self.symbol,
            side=self.side,
            order_quantity=normalize_decimal(self.order_quantity),
            cumulative_quantity=normalize_decimal(
                self.cumulative_quantity
            ),
            remaining_quantity=normalize_decimal(
                self.order_quantity - self.cumulative_quantity
            ),
            cumulative_notional=normalize_decimal(
                self.cumulative_notional
            ),
            cumulative_vwap=self.vwap(),
            fill_count=len(self._fills),
            complete=(
                self.cumulative_quantity == self.order_quantity
            ),
            generated_at=utc_now(),
        )

    def export(self) -> dict[str, Any]:
        return {
            "schema_version": "v36.2.fill_ledger.1",
            "version": VERSION,
            "snapshot": asdict(self.snapshot()),
            "fills": [asdict(item) for item in self.ledger()],
            "network_used": False,
        }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def demo_engine(
    *,
    symbol: str,
    side: str,
    order_quantity: str,
    first_quantity: str,
    first_price: str,
    second_quantity: str,
    second_price: str,
) -> dict[str, Any]:
    engine = PartialFillEngine(
        order_id=f"order-{uuid.uuid4().hex}",
        symbol=symbol,
        side=side,
        order_quantity=order_quantity,
    )

    receipts = [
        asdict(
            engine.apply_fill(
                trade_id="trade-001",
                quantity=first_quantity,
                price=first_price,
            )
        ),
        asdict(
            engine.apply_fill(
                trade_id="trade-002",
                quantity=second_quantity,
                price=second_price,
            )
        ),
    ]

    return {
        "schema_version": "v36.2.partial_fill_demo.1",
        "version": VERSION,
        "receipts": receipts,
        "ledger": engine.export(),
        "network_used": False,
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="V36.2 Partial Fill Engine"
    )
    p.add_argument("--symbol", default="AAPL")
    p.add_argument("--side", choices=["buy", "sell"], default="buy")
    p.add_argument("--order-quantity", default="10")
    p.add_argument("--first-quantity", default="4")
    p.add_argument("--first-price", default="200")
    p.add_argument("--second-quantity", default="6")
    p.add_argument("--second-price", default="210")
    p.add_argument(
        "--output",
        default="release/v36/audit/partial_fill_result_v36_2.json",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    payload = demo_engine(
        symbol=args.symbol,
        side=args.side,
        order_quantity=args.order_quantity,
        first_quantity=args.first_quantity,
        first_price=args.first_price,
        second_quantity=args.second_quantity,
        second_price=args.second_price,
    )
    write_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
