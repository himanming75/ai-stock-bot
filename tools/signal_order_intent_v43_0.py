#!/usr/bin/env python3
"""
V43.0 Signal & Order Intent Foundation

Transforms a V42 strategy result into a deterministic order intent.

Features:
- BUY / SELL / HOLD signal normalization
- confidence threshold gate
- stale-signal rejection
- duplicate signal rejection
- deterministic client_order_id
- optional cash-based quantity sizing
- SHA-256 signal and intent receipts
- offline-only behavior
- explicit live-mode safety gate

No broker calls and no network calls are performed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from pathlib import Path
from typing import Any, Sequence


VERSION = "43.0"


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


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
class SignalInput:
    symbol: str
    decision: str
    confidence: int
    latest_price: str
    generated_at: str
    source_sha256: str
    strategy_version: str = "42.0"


@dataclass(frozen=True)
class IntentConfig:
    minimum_confidence: int = 60
    max_signal_age_seconds: int = 300
    cash_allocation_pct: str = "0.10"
    max_quantity: int = 1000
    allow_fractional: bool = False

    def validate(self) -> None:
        if not 0 <= self.minimum_confidence <= 100:
            raise ValueError("minimum_confidence must be between 0 and 100")
        if self.max_signal_age_seconds < 0:
            raise ValueError("max_signal_age_seconds must be zero or greater")
        allocation = to_decimal(self.cash_allocation_pct, "cash_allocation_pct")
        if allocation <= 0 or allocation > 1:
            raise ValueError("cash_allocation_pct must be greater than 0 and at most 1")
        if self.max_quantity <= 0:
            raise ValueError("max_quantity must be greater than zero")


@dataclass(frozen=True)
class OrderIntent:
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


class SignalOrderIntentEngine:
    def __init__(
        self,
        config: IntentConfig | None = None,
        *,
        mode: str = "paper",
        enable_live: bool = False,
        reference_time: str | None = None,
    ) -> None:
        self.config = config or IntentConfig()
        self.config.validate()
        if mode not in {"replay", "paper", "live"}:
            raise ValueError("mode must be replay, paper, or live")
        self.mode = mode
        self.enable_live = enable_live
        self.reference_time = (
            parse_timestamp(reference_time) if reference_time else datetime.now(timezone.utc)
        )
        self._seen_signal_hashes: set[str] = set()

    def _live_gate(self) -> None:
        if self.mode == "live":
            if not self.enable_live:
                raise PermissionError("live mode requires --enable-live")
            raise NotImplementedError(
                "broker transport is intentionally not implemented in V43.0"
            )

    def _size_quantity(
        self,
        *,
        price: Decimal,
        available_cash: Decimal,
        explicit_quantity: Decimal | None,
    ) -> Decimal:
        if explicit_quantity is not None:
            quantity = explicit_quantity
        else:
            budget = available_cash * to_decimal(
                self.config.cash_allocation_pct,
                "cash_allocation_pct",
            )
            quantity = budget / price

        if not self.config.allow_fractional:
            quantity = quantity.to_integral_value(rounding=ROUND_DOWN)

        max_qty = Decimal(self.config.max_quantity)
        if quantity > max_qty:
            quantity = max_qty
        if quantity <= 0:
            raise ValueError("calculated quantity must be greater than zero")
        return quantity

    def create_intent(
        self,
        signal: SignalInput,
        *,
        available_cash: Any = "100000",
        quantity: Any | None = None,
        order_type: str = "market",
        limit_price: Any | None = None,
        time_in_force: str = "day",
    ) -> OrderIntent:
        self._live_gate()

        symbol = signal.symbol.strip().upper()
        decision = signal.decision.strip().upper()
        reasons: list[str] = []

        if not symbol:
            reasons.append("Symbol is required.")
        if decision not in {"BUY", "SELL", "HOLD"}:
            reasons.append("Decision must be BUY, SELL, or HOLD.")
        if not 0 <= signal.confidence <= 100:
            reasons.append("Confidence must be between 0 and 100.")
        if len(signal.source_sha256) != 64:
            reasons.append("Source signal SHA-256 must contain 64 hexadecimal characters.")
        else:
            try:
                int(signal.source_sha256, 16)
            except ValueError:
                reasons.append("Source signal SHA-256 must be hexadecimal.")

        generated = parse_timestamp(signal.generated_at)
        age = self.reference_time - generated
        if age > timedelta(seconds=self.config.max_signal_age_seconds):
            reasons.append("Signal is stale.")
        if generated - self.reference_time > timedelta(seconds=5):
            reasons.append("Signal timestamp is in the future.")

        if signal.source_sha256 in self._seen_signal_hashes:
            reasons.append("Duplicate signal was already processed.")

        if signal.confidence < self.config.minimum_confidence:
            reasons.append("Signal confidence is below the configured minimum.")

        normalized_order_type = order_type.strip().lower()
        if normalized_order_type not in {"market", "limit"}:
            reasons.append("Order type must be market or limit.")

        tif = time_in_force.strip().lower()
        if tif not in {"day", "gtc"}:
            reasons.append("Time in force must be day or gtc.")

        price = positive_decimal(signal.latest_price, "latest_price")
        cash = nonnegative_decimal(available_cash, "available_cash")

        normalized_limit: str | None = None
        if normalized_order_type == "limit":
            if limit_price is None:
                reasons.append("Limit price is required for a limit order.")
            else:
                normalized_limit = normalize(
                    positive_decimal(limit_price, "limit_price")
                )
        elif limit_price is not None:
            reasons.append("Limit price must be omitted for a market order.")

        side: str | None = None
        qty = Decimal("0")
        status = "REJECTED"
        client_order_id: str | None = None

        if decision == "HOLD":
            reasons.append("HOLD signals do not create executable order intents.")

        if not reasons:
            side = "buy" if decision == "BUY" else "sell"
            explicit_qty = (
                positive_decimal(quantity, "quantity") if quantity is not None else None
            )
            qty = self._size_quantity(
                price=price,
                available_cash=cash,
                explicit_quantity=explicit_qty,
            )
            seed = {
                "symbol": symbol,
                "decision": decision,
                "side": side,
                "quantity": normalize(qty),
                "order_type": normalized_order_type,
                "limit_price": normalized_limit,
                "time_in_force": tif,
                "source_signal_sha256": signal.source_sha256,
            }
            client_order_id = f"v43-{canonical_hash(seed)[:24]}"
            status = "ACCEPTED"
            self._seen_signal_hashes.add(signal.source_sha256)

        expires = generated + timedelta(
            seconds=self.config.max_signal_age_seconds
        )

        core = {
            "schema_version": "v43.0.order_intent.1",
            "version": VERSION,
            "status": status,
            "symbol": symbol,
            "signal_decision": decision,
            "side": side,
            "quantity": normalize(qty),
            "order_type": normalized_order_type,
            "time_in_force": tif,
            "limit_price": normalized_limit,
            "confidence": signal.confidence,
            "generated_at": generated.isoformat(),
            "expires_at": expires.isoformat(),
            "client_order_id": client_order_id,
            "source_signal_sha256": signal.source_sha256,
            "rejection_reasons": reasons,
            "network_used": False,
        }
        return OrderIntent(**core, intent_sha256=canonical_hash(core))

    @staticmethod
    def export(path: Path, intent: OrderIntent) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "v43.0.order_intent_export.1",
            "version": VERSION,
            "intent": asdict(intent),
            "network_used": False,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_strategy_result(path: Path) -> SignalInput:
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = payload.get("result", payload)
    required = [
        "symbol",
        "decision",
        "confidence",
        "latest_price",
        "decision_sha256",
    ]
    missing = [name for name in required if name not in result]
    if missing:
        raise ValueError(f"missing strategy fields: {', '.join(missing)}")
    return SignalInput(
        symbol=str(result["symbol"]),
        decision=str(result["decision"]),
        confidence=int(result["confidence"]),
        latest_price=str(result["latest_price"]),
        generated_at=str(
            result.get("generated_at")
            or payload.get("generated_at")
            or utc_now()
        ),
        source_sha256=str(result["decision_sha256"]),
        strategy_version=str(result.get("version", "42.0")),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="V43.0 Signal & Order Intent Foundation"
    )
    parser.add_argument("--input")
    parser.add_argument("--symbol", default="AAPL")
    parser.add_argument("--decision", choices=["BUY", "SELL", "HOLD"], default="BUY")
    parser.add_argument("--confidence", type=int, default=90)
    parser.add_argument("--latest-price", default="200")
    parser.add_argument("--generated-at")
    parser.add_argument("--source-sha256")
    parser.add_argument("--available-cash", default="100000")
    parser.add_argument("--quantity")
    parser.add_argument("--order-type", choices=["market", "limit"], default="market")
    parser.add_argument("--limit-price")
    parser.add_argument("--time-in-force", choices=["day", "gtc"], default="day")
    parser.add_argument("--minimum-confidence", type=int, default=60)
    parser.add_argument("--max-signal-age-seconds", type=int, default=300)
    parser.add_argument("--cash-allocation-pct", default="0.10")
    parser.add_argument("--max-quantity", type=int, default=1000)
    parser.add_argument("--allow-fractional", action="store_true")
    parser.add_argument("--mode", choices=["replay", "paper", "live"], default="paper")
    parser.add_argument("--enable-live", action="store_true")
    parser.add_argument("--reference-time")
    parser.add_argument(
        "--output",
        default="release/v43/audit/order_intent_result_v43_0.json",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    generated_at = args.generated_at or utc_now()
    reference_time = args.reference_time or generated_at
    source_sha = args.source_sha256 or canonical_hash(
        {
            "symbol": args.symbol.upper(),
            "decision": args.decision,
            "confidence": args.confidence,
            "latest_price": args.latest_price,
            "generated_at": generated_at,
        }
    )

    config = IntentConfig(
        minimum_confidence=args.minimum_confidence,
        max_signal_age_seconds=args.max_signal_age_seconds,
        cash_allocation_pct=args.cash_allocation_pct,
        max_quantity=args.max_quantity,
        allow_fractional=args.allow_fractional,
    )

    engine = SignalOrderIntentEngine(
        config,
        mode=args.mode,
        enable_live=args.enable_live,
        reference_time=reference_time,
    )

    try:
        signal = (
            load_strategy_result(Path(args.input))
            if args.input
            else SignalInput(
                symbol=args.symbol,
                decision=args.decision,
                confidence=args.confidence,
                latest_price=args.latest_price,
                generated_at=generated_at,
                source_sha256=source_sha,
            )
        )
        intent = engine.create_intent(
            signal,
            available_cash=args.available_cash,
            quantity=args.quantity,
            order_type=args.order_type,
            limit_price=args.limit_price,
            time_in_force=args.time_in_force,
        )
        engine.export(Path(args.output), intent)
        print(json.dumps(asdict(intent), indent=2, sort_keys=True))
        return 0 if intent.status == "ACCEPTED" else 1
    except (ValueError, PermissionError, NotImplementedError) as exc:
        error = {
            "schema_version": "v43.0.order_intent_error.1",
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
