#!/usr/bin/env python3
"""
V31.0 Live Trading Readiness Foundation

This module intentionally does NOT connect to a broker or submit live orders.

Features:
- Broker adapter protocol
- Paper/live account mode separation
- Order request validation
- Dry-run execution receipts
- Double-lock live trading gate
- Explicit rejection of live orders unless all gates pass
- Deterministic JSON audit receipts

Live mode requires BOTH:
1. A local approval file with exact schema and confirmation phrase
2. An explicit runtime flag

Even when both are present, this V31.0 foundation still returns a simulated
receipt because no real broker transport is implemented.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, Sequence


VERSION = "31.0"
LIVE_CONFIRMATION_PHRASE = "I UNDERSTAND THIS ENABLES LIVE ORDER ROUTING"
APPROVAL_SCHEMA = "v31.0.live_trading_approval.1"


class TradingMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class TimeInForce(str, Enum):
    DAY = "day"
    GTC = "gtc"


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: OrderSide
    quantity: str
    order_type: OrderType
    time_in_force: TimeInForce = TimeInForce.DAY
    limit_price: str | None = None
    client_order_id: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: list[str]
    normalized_order: dict[str, Any] | None


@dataclass(frozen=True)
class ExecutionReceipt:
    schema_version: str
    version: str
    receipt_id: str
    generated_at: str
    mode: str
    status: str
    broker: str
    dry_run: bool
    live_transport_implemented: bool
    normalized_order: dict[str, Any] | None
    validation_errors: list[str]
    gate_reasons: list[str]
    order_sha256: str | None


class BrokerAdapter(Protocol):
    @property
    def name(self) -> str: ...

    def health_check(self) -> dict[str, Any]: ...

    def submit_order(self, order: dict[str, Any]) -> dict[str, Any]: ...


class NullBrokerAdapter:
    """Safe adapter that never sends orders anywhere."""

    @property
    def name(self) -> str:
        return "null-broker-v31"

    def health_check(self) -> dict[str, Any]:
        return {
            "status": "PASS",
            "connected": False,
            "transport": "none",
            "live_order_capable": False,
        }

    def submit_order(self, order: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError(
            "NullBrokerAdapter cannot submit orders. "
            "No live broker transport is implemented in V31.0."
        )


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_json(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_payload(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload)).hexdigest()


def decimal_string(value: str, field: str) -> tuple[str | None, str | None]:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None, f"{field} must be numeric"
    if not number.is_finite():
        return None, f"{field} must be finite"
    if number <= 0:
        return None, f"{field} must be greater than zero"
    normalized = format(number.normalize(), "f")
    return normalized, None


def validate_order(order: OrderRequest) -> ValidationResult:
    errors: list[str] = []

    symbol = order.symbol.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,14}", symbol):
        errors.append("symbol must be a valid uppercase market symbol")

    quantity, quantity_error = decimal_string(order.quantity, "quantity")
    if quantity_error:
        errors.append(quantity_error)

    limit_price: str | None = None
    if order.order_type == OrderType.LIMIT:
        if order.limit_price is None:
            errors.append("limit_price is required for limit orders")
        else:
            limit_price, price_error = decimal_string(
                order.limit_price, "limit_price"
            )
            if price_error:
                errors.append(price_error)
    elif order.limit_price is not None:
        errors.append("limit_price must be omitted for market orders")

    client_order_id = (
        order.client_order_id.strip()
        if order.client_order_id
        else f"v31-{uuid.uuid4().hex[:20]}"
    )
    if not re.fullmatch(r"[A-Za-z0-9._\-]{4,64}", client_order_id):
        errors.append(
            "client_order_id must be 4-64 characters using letters, "
            "numbers, dot, underscore, or hyphen"
        )

    normalized = None
    if not errors:
        normalized = {
            "symbol": symbol,
            "side": order.side.value,
            "quantity": quantity,
            "order_type": order.order_type.value,
            "time_in_force": order.time_in_force.value,
            "limit_price": limit_price,
            "client_order_id": client_order_id,
        }

    return ValidationResult(
        valid=not errors,
        errors=errors,
        normalized_order=normalized,
    )


def load_live_approval(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    reasons: list[str] = []
    if not path.is_file():
        return None, [f"Live approval file is missing: {path}"]

    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return None, [f"Live approval file parse error: {type(exc).__name__}: {exc}"]

    if not isinstance(payload, dict):
        return None, ["Live approval file must contain a JSON object"]

    if payload.get("schema_version") != APPROVAL_SCHEMA:
        reasons.append("Live approval schema_version is invalid")
    if payload.get("approved") is not True:
        reasons.append("Live approval must set approved=true")
    if payload.get("confirmation_phrase") != LIVE_CONFIRMATION_PHRASE:
        reasons.append("Live approval confirmation phrase is invalid")
    if payload.get("paper_trading_tests_passed") is not True:
        reasons.append("Live approval must confirm paper trading tests passed")
    if payload.get("risk_review_passed") is not True:
        reasons.append("Live approval must confirm risk review passed")

    return payload, reasons


def evaluate_live_gate(
    mode: TradingMode,
    runtime_live_flag: bool,
    approval_file: Path | None,
) -> tuple[bool, list[str]]:
    if mode == TradingMode.PAPER:
        return True, []

    reasons: list[str] = []
    if not runtime_live_flag:
        reasons.append("Runtime --enable-live flag was not provided")
    if approval_file is None:
        reasons.append("No live approval file was provided")
    else:
        _, approval_reasons = load_live_approval(approval_file)
        reasons.extend(approval_reasons)

    return not reasons, reasons


def execute_order(
    order: OrderRequest,
    mode: TradingMode,
    adapter: BrokerAdapter | None = None,
    runtime_live_flag: bool = False,
    approval_file: Path | None = None,
) -> ExecutionReceipt:
    adapter = adapter or NullBrokerAdapter()
    validation = validate_order(order)
    gate_open, gate_reasons = evaluate_live_gate(
        mode=mode,
        runtime_live_flag=runtime_live_flag,
        approval_file=approval_file,
    )

    if not validation.valid:
        status = "REJECTED_VALIDATION"
    elif not gate_open:
        status = "REJECTED_LIVE_GATE"
    elif mode == TradingMode.LIVE:
        # Intentionally simulated: V31.0 has no broker network transport.
        status = "SIMULATED_LIVE_READY_NO_TRANSPORT"
    else:
        status = "DRY_RUN_ACCEPTED"

    normalized = validation.normalized_order
    return ExecutionReceipt(
        schema_version="v31.0.execution_receipt.1",
        version=VERSION,
        receipt_id=f"rcpt-{uuid.uuid4().hex}",
        generated_at=utc_now(),
        mode=mode.value,
        status=status,
        broker=adapter.name,
        dry_run=True,
        live_transport_implemented=False,
        normalized_order=normalized,
        validation_errors=validation.errors,
        gate_reasons=gate_reasons,
        order_sha256=sha256_payload(normalized) if normalized else None,
    )


def write_receipt(path: Path, receipt: ExecutionReceipt) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(receipt), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def create_approval_template(path: Path) -> None:
    payload = {
        "schema_version": APPROVAL_SCHEMA,
        "approved": False,
        "confirmation_phrase": "",
        "paper_trading_tests_passed": False,
        "risk_review_passed": False,
        "approved_by": "",
        "approved_at": "",
        "notes": "Template only. Do not set approved=true without a separate review.",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="V31.0 Live Trading Readiness Foundation"
    )
    p.add_argument("--symbol", default="AAPL")
    p.add_argument("--side", choices=[v.value for v in OrderSide], default="buy")
    p.add_argument("--quantity", default="1")
    p.add_argument(
        "--order-type",
        choices=[v.value for v in OrderType],
        default="market",
    )
    p.add_argument("--limit-price", default=None)
    p.add_argument(
        "--time-in-force",
        choices=[v.value for v in TimeInForce],
        default="day",
    )
    p.add_argument("--client-order-id", default=None)
    p.add_argument(
        "--mode",
        choices=[v.value for v in TradingMode],
        default="paper",
    )
    p.add_argument("--enable-live", action="store_true")
    p.add_argument("--approval-file", default=None)
    p.add_argument(
        "--receipt-output",
        default="release/v31/audit/live_readiness_receipt_v31_0.json",
    )
    p.add_argument(
        "--create-approval-template",
        default=None,
        help="Create a disabled live approval template and exit",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)

    if args.create_approval_template:
        path = Path(args.create_approval_template)
        create_approval_template(path)
        print(json.dumps({
            "status": "PASS",
            "template_path": str(path.resolve()),
            "approved": False,
        }, indent=2))
        return 0

    order = OrderRequest(
        symbol=args.symbol,
        side=OrderSide(args.side),
        quantity=args.quantity,
        order_type=OrderType(args.order_type),
        time_in_force=TimeInForce(args.time_in_force),
        limit_price=args.limit_price,
        client_order_id=args.client_order_id,
    )
    approval = Path(args.approval_file) if args.approval_file else None
    receipt = execute_order(
        order=order,
        mode=TradingMode(args.mode),
        runtime_live_flag=args.enable_live,
        approval_file=approval,
    )
    output = Path(args.receipt_output)
    write_receipt(output, receipt)
    print(json.dumps(asdict(receipt), indent=2, sort_keys=True))

    accepted_statuses = {
        "DRY_RUN_ACCEPTED",
        "SIMULATED_LIVE_READY_NO_TRANSPORT",
    }
    return 0 if receipt.status in accepted_statuses else 1


if __name__ == "__main__":
    raise SystemExit(main())
