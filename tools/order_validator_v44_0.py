#!/usr/bin/env python3
"""
V44.0 Order Validator Foundation

Validates V43 order intents before any risk or execution layer.

Checks:
- intent status and core fields
- BUY / SELL side
- market / limit order rules
- quantity, lot size, and tick size
- minimum and maximum order notional
- cash / buying power for BUY
- position quantity for SELL
- market open, halt, and delisted status
- expiration and client_order_id duplication
- SHA-256 intent integrity
- offline-only execution and live safety gate

No broker or network calls are performed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Sequence


VERSION = "44.0"


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def to_decimal(value: Any, name: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not number.is_finite():
        raise ValueError(f"{name} must be finite")
    return number


def positive_decimal(value: Any, name: str) -> Decimal:
    number = to_decimal(value, name)
    if number <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return number


def nonnegative_decimal(value: Any, name: str) -> Decimal:
    number = to_decimal(value, name)
    if number < 0:
        raise ValueError(f"{name} must be zero or greater")
    return number


def normalize(number: Decimal) -> str:
    if number == 0:
        return "0"
    return format(number.normalize(), "f")


@dataclass(frozen=True)
class ValidationConfig:
    tick_size: str = "0.01"
    lot_size: str = "1"
    minimum_notional: str = "1"
    maximum_notional: str = "25000"

    def validate(self) -> None:
        positive_decimal(self.tick_size, "tick_size")
        positive_decimal(self.lot_size, "lot_size")
        positive_decimal(self.minimum_notional, "minimum_notional")
        positive_decimal(self.maximum_notional, "maximum_notional")
        if to_decimal(self.minimum_notional, "minimum_notional") > to_decimal(
            self.maximum_notional, "maximum_notional"
        ):
            raise ValueError("minimum_notional cannot exceed maximum_notional")


@dataclass(frozen=True)
class OrderIntentInput:
    schema_version: str
    version: str
    status: str
    symbol: str
    signal_decision: str
    side: str | None
    quantity: str
    order_type: str
    time_in_force: str
    limit_price: str | None
    confidence: int
    generated_at: str
    expires_at: str
    client_order_id: str | None
    source_signal_sha256: str
    rejection_reasons: list[str]
    network_used: bool
    intent_sha256: str


@dataclass(frozen=True)
class ValidationResult:
    schema_version: str
    version: str
    status: str
    symbol: str
    client_order_id: str | None
    side: str | None
    quantity: str
    reference_price: str | None
    order_notional: str | None
    checks: list[dict[str, Any]]
    rejection_reasons: list[str]
    network_used: bool
    validation_sha256: str


class OrderValidator:
    def __init__(
        self,
        config: ValidationConfig | None = None,
        *,
        mode: str = "paper",
        enable_live: bool = False,
        reference_time: str | None = None,
    ) -> None:
        self.config = config or ValidationConfig()
        self.config.validate()
        if mode not in {"replay", "paper", "live"}:
            raise ValueError("mode must be replay, paper, or live")
        self.mode = mode
        self.enable_live = enable_live
        self.reference_time = (
            parse_timestamp(reference_time)
            if reference_time
            else datetime.now(timezone.utc)
        )
        self._seen_client_order_ids: set[str] = set()

    def _live_gate(self) -> None:
        if self.mode == "live":
            if not self.enable_live:
                raise PermissionError("live mode requires --enable-live")
            raise NotImplementedError(
                "live broker submission is intentionally not implemented in V44.0"
            )

    @staticmethod
    def _intent_hash_payload(intent: OrderIntentInput) -> dict[str, Any]:
        return {
            "schema_version": intent.schema_version,
            "version": intent.version,
            "status": intent.status,
            "symbol": intent.symbol,
            "signal_decision": intent.signal_decision,
            "side": intent.side,
            "quantity": intent.quantity,
            "order_type": intent.order_type,
            "time_in_force": intent.time_in_force,
            "limit_price": intent.limit_price,
            "confidence": intent.confidence,
            "generated_at": intent.generated_at,
            "expires_at": intent.expires_at,
            "client_order_id": intent.client_order_id,
            "source_signal_sha256": intent.source_signal_sha256,
            "rejection_reasons": intent.rejection_reasons,
            "network_used": intent.network_used,
        }

    def validate(
        self,
        intent: OrderIntentInput,
        *,
        market_price: Any | None,
        available_cash: Any = "100000",
        buying_power: Any = "100000",
        position_quantity: Any = "0",
        market_open: bool = True,
        halted: bool = False,
        delisted: bool = False,
    ) -> ValidationResult:
        self._live_gate()

        checks: list[dict[str, Any]] = []
        reasons: list[str] = []

        def record(check_id: str, passed: bool, message: str) -> None:
            checks.append(
                {
                    "check_id": check_id,
                    "status": "PASS" if passed else "FAIL",
                    "message": message,
                }
            )
            if not passed:
                reasons.append(message)

        symbol = intent.symbol.strip().upper()
        side = intent.side.lower() if intent.side else None
        order_type = intent.order_type.lower()
        tif = intent.time_in_force.lower()

        record(
            "intent.accepted",
            intent.status == "ACCEPTED",
            "Intent status must be ACCEPTED.",
        )
        record("symbol.present", bool(symbol), "Symbol is required.")
        record("side.valid", side in {"buy", "sell"}, "Side must be buy or sell.")
        record(
            "order_type.valid",
            order_type in {"market", "limit"},
            "Order type must be market or limit.",
        )
        record(
            "time_in_force.valid",
            tif in {"day", "gtc"},
            "Time in force must be day or gtc.",
        )
        record("market.open", market_open, "Market is closed.")
        record("market.not_halted", not halted, "Symbol is halted.")
        record("symbol.not_delisted", not delisted, "Symbol is delisted.")

        try:
            quantity = positive_decimal(intent.quantity, "quantity")
            record("quantity.positive", True, "Quantity is valid.")
        except ValueError as exc:
            quantity = Decimal("0")
            record("quantity.positive", False, str(exc))

        lot_size = to_decimal(self.config.lot_size, "lot_size")
        lot_ok = quantity > 0 and quantity % lot_size == 0
        record(
            "quantity.lot_size",
            lot_ok,
            f"Quantity must be a multiple of lot size {normalize(lot_size)}.",
        )

        if order_type == "market":
            record(
                "market_order.no_limit_price",
                intent.limit_price is None,
                "Market orders must not include a limit price.",
            )
        elif order_type == "limit":
            record(
                "limit_order.has_limit_price",
                intent.limit_price is not None,
                "Limit orders require a limit price.",
            )

        reference_price: Decimal | None = None
        if order_type == "limit" and intent.limit_price is not None:
            try:
                reference_price = positive_decimal(intent.limit_price, "limit_price")
            except ValueError as exc:
                record("limit_price.positive", False, str(exc))
        elif order_type == "market":
            try:
                reference_price = positive_decimal(market_price, "market_price")
            except ValueError as exc:
                record("market_price.positive", False, str(exc))

        if reference_price is not None:
            tick_size = to_decimal(self.config.tick_size, "tick_size")
            tick_ok = reference_price % tick_size == 0
            record(
                "price.tick_size",
                tick_ok,
                f"Price must conform to tick size {normalize(tick_size)}.",
            )

        try:
            expires_at = parse_timestamp(intent.expires_at)
            record(
                "intent.not_expired",
                self.reference_time <= expires_at,
                "Order intent is expired.",
            )
        except ValueError as exc:
            record("intent.not_expired", False, str(exc))

        expected_hash = canonical_hash(self._intent_hash_payload(intent))
        record(
            "intent.hash",
            expected_hash == intent.intent_sha256,
            "Intent SHA-256 verification failed.",
        )

        client_order_id = intent.client_order_id
        record(
            "client_order_id.present",
            bool(client_order_id),
            "client_order_id is required.",
        )
        duplicate = bool(
            client_order_id and client_order_id in self._seen_client_order_ids
        )
        record(
            "client_order_id.unique",
            not duplicate,
            "Duplicate client_order_id was already validated.",
        )

        order_notional: Decimal | None = None
        if quantity > 0 and reference_price is not None:
            order_notional = quantity * reference_price
            minimum = to_decimal(self.config.minimum_notional, "minimum_notional")
            maximum = to_decimal(self.config.maximum_notional, "maximum_notional")
            record(
                "notional.minimum",
                order_notional >= minimum,
                f"Order notional is below the minimum {normalize(minimum)}.",
            )
            record(
                "notional.maximum",
                order_notional <= maximum,
                f"Order notional exceeds the maximum {normalize(maximum)}.",
            )

            if side == "buy":
                cash = nonnegative_decimal(available_cash, "available_cash")
                power = nonnegative_decimal(buying_power, "buying_power")
                record(
                    "account.cash",
                    cash >= order_notional,
                    "Available cash is insufficient.",
                )
                record(
                    "account.buying_power",
                    power >= order_notional,
                    "Buying power is insufficient.",
                )
            elif side == "sell":
                held = nonnegative_decimal(position_quantity, "position_quantity")
                record(
                    "position.quantity",
                    held >= quantity,
                    "Position quantity is insufficient for the sell order.",
                )

        status = "PASS" if not reasons else "FAIL"
        if status == "PASS" and client_order_id:
            self._seen_client_order_ids.add(client_order_id)

        core = {
            "schema_version": "v44.0.order_validation.1",
            "version": VERSION,
            "status": status,
            "symbol": symbol,
            "client_order_id": client_order_id,
            "side": side,
            "quantity": normalize(quantity),
            "reference_price": (
                normalize(reference_price) if reference_price is not None else None
            ),
            "order_notional": (
                normalize(order_notional) if order_notional is not None else None
            ),
            "checks": checks,
            "rejection_reasons": reasons,
            "network_used": False,
        }
        return ValidationResult(**core, validation_sha256=canonical_hash(core))

    @staticmethod
    def export(path: Path, result: ValidationResult) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "v44.0.order_validation_export.1",
            "version": VERSION,
            "result": asdict(result),
            "network_used": False,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_intent(path: Path) -> OrderIntentInput:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("intent", payload)
    return OrderIntentInput(**raw)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V44.0 Order Validator Foundation")
    parser.add_argument(
        "--input",
        default="release/v43/audit/order_intent_result_v43_0.json",
    )
    parser.add_argument("--market-price", default="200")
    parser.add_argument("--available-cash", default="100000")
    parser.add_argument("--buying-power", default="100000")
    parser.add_argument("--position-quantity", default="0")
    parser.add_argument("--market-open", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--halted", action="store_true")
    parser.add_argument("--delisted", action="store_true")
    parser.add_argument("--tick-size", default="0.01")
    parser.add_argument("--lot-size", default="1")
    parser.add_argument("--minimum-notional", default="1")
    parser.add_argument("--maximum-notional", default="25000")
    parser.add_argument("--mode", choices=["replay", "paper", "live"], default="paper")
    parser.add_argument("--enable-live", action="store_true")
    parser.add_argument("--reference-time")
    parser.add_argument(
        "--output",
        default="release/v44/audit/order_validation_result_v44_0.json",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    validator = OrderValidator(
        ValidationConfig(
            tick_size=args.tick_size,
            lot_size=args.lot_size,
            minimum_notional=args.minimum_notional,
            maximum_notional=args.maximum_notional,
        ),
        mode=args.mode,
        enable_live=args.enable_live,
        reference_time=args.reference_time,
    )

    try:
        intent = load_intent(Path(args.input))
        result = validator.validate(
            intent,
            market_price=args.market_price,
            available_cash=args.available_cash,
            buying_power=args.buying_power,
            position_quantity=args.position_quantity,
            market_open=args.market_open,
            halted=args.halted,
            delisted=args.delisted,
        )
        validator.export(Path(args.output), result)
        print(json.dumps(asdict(result), indent=2, sort_keys=True))
        return 0 if result.status == "PASS" else 1
    except (TypeError, ValueError, PermissionError, NotImplementedError) as exc:
        error = {
            "schema_version": "v44.0.order_validation_error.1",
            "version": VERSION,
            "status": "FAIL",
            "error": str(exc),
            "network_used": False,
        }
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(error, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(error, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
