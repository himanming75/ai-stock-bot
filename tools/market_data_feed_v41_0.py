#!/usr/bin/env python3
"""
V41.0 Market Data Feed Foundation

Provides a deterministic, network-disabled market-data layer for:
- quote and trade normalization
- bid/ask validation
- stale-data rejection
- deterministic replay
- SHA-256 event and snapshot receipts
- explicit live-mode safety gate

No external network calls are performed in V41.0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Sequence


VERSION = "41.0"


class FeedStatus(str, Enum):
    ACCEPTED = "accepted"
    REJECTED_INVALID = "rejected_invalid"
    REJECTED_STALE = "rejected_stale"
    REJECTED_LIVE_GATE = "rejected_live_gate"


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


def dec(value: Any, name: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not number.is_finite():
        raise ValueError(f"{name} must be finite")
    return number


def pos(value: Any, name: str) -> Decimal:
    number = dec(value, name)
    if number <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return number


def nonneg(value: Any, name: str) -> Decimal:
    number = dec(value, name)
    if number < 0:
        raise ValueError(f"{name} must be zero or greater")
    return number


def norm(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def parse_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class QuoteInput:
    symbol: str
    bid: str
    ask: str
    bid_size: str
    ask_size: str
    timestamp: str
    source: str = "offline"


@dataclass(frozen=True)
class TradeInput:
    symbol: str
    price: str
    size: str
    timestamp: str
    source: str = "offline"


@dataclass(frozen=True)
class MarketDataEvent:
    event_type: str
    symbol: str
    timestamp: str
    source: str
    payload: dict[str, str]
    event_sha256: str


@dataclass(frozen=True)
class FeedReceipt:
    schema_version: str
    version: str
    status: str
    mode: str
    symbol: str | None
    accepted_event_count: int
    rejected_event_count: int
    last_price: str | None
    bid: str | None
    ask: str | None
    midpoint: str | None
    spread: str | None
    generated_at: str
    network_used: bool
    rejection_reasons: list[str]
    snapshot_sha256: str


class MarketDataFeed:
    def __init__(
        self,
        *,
        max_age_seconds: int = 60,
        reference_time: str | None = None,
        mode: str = "replay",
        enable_live: bool = False,
    ) -> None:
        if max_age_seconds < 0:
            raise ValueError("max_age_seconds must be zero or greater")
        if mode not in {"replay", "paper", "live"}:
            raise ValueError("mode must be replay, paper, or live")
        self.max_age_seconds = max_age_seconds
        self.reference_time = (
            parse_timestamp(reference_time) if reference_time else datetime.now(timezone.utc)
        )
        self.mode = mode
        self.enable_live = enable_live
        self._events: list[MarketDataEvent] = []
        self._rejections: list[str] = []
        self._last_quote: MarketDataEvent | None = None
        self._last_trade: MarketDataEvent | None = None

    def _live_gate(self) -> None:
        if self.mode == "live":
            if not self.enable_live:
                raise PermissionError(
                    "live mode requires --enable-live and an implemented network transport"
                )
            raise NotImplementedError(
                "network transport is intentionally not implemented in V41.0"
            )

    def _is_stale(self, timestamp: datetime) -> bool:
        return self.reference_time - timestamp > timedelta(seconds=self.max_age_seconds)

    def accept_quote(self, quote: QuoteInput) -> MarketDataEvent:
        self._live_gate()
        symbol = quote.symbol.strip().upper()
        if not symbol:
            raise ValueError("symbol is required")
        bid = pos(quote.bid, "bid")
        ask = pos(quote.ask, "ask")
        bid_size = nonneg(quote.bid_size, "bid_size")
        ask_size = nonneg(quote.ask_size, "ask_size")
        timestamp = parse_timestamp(quote.timestamp)
        if bid > ask:
            raise ValueError("bid must not exceed ask")
        if self._is_stale(timestamp):
            raise TimeoutError("quote is stale")

        payload = {
            "bid": norm(bid),
            "ask": norm(ask),
            "bid_size": norm(bid_size),
            "ask_size": norm(ask_size),
        }
        core = {
            "event_type": "quote",
            "symbol": symbol,
            "timestamp": timestamp.isoformat(),
            "source": quote.source,
            "payload": payload,
        }
        event = MarketDataEvent(**core, event_sha256=canonical_hash(core))
        self._events.append(event)
        self._last_quote = event
        return event

    def accept_trade(self, trade: TradeInput) -> MarketDataEvent:
        self._live_gate()
        symbol = trade.symbol.strip().upper()
        if not symbol:
            raise ValueError("symbol is required")
        price = pos(trade.price, "price")
        size = pos(trade.size, "size")
        timestamp = parse_timestamp(trade.timestamp)
        if self._is_stale(timestamp):
            raise TimeoutError("trade is stale")

        payload = {"price": norm(price), "size": norm(size)}
        core = {
            "event_type": "trade",
            "symbol": symbol,
            "timestamp": timestamp.isoformat(),
            "source": trade.source,
            "payload": payload,
        }
        event = MarketDataEvent(**core, event_sha256=canonical_hash(core))
        self._events.append(event)
        self._last_trade = event
        return event

    def replay(self, records: Iterable[dict[str, Any]]) -> FeedReceipt:
        accepted = 0
        rejected = 0
        symbols: set[str] = set()

        for index, record in enumerate(records):
            try:
                event_type = str(record.get("type", "")).lower()
                if event_type == "quote":
                    event = self.accept_quote(
                        QuoteInput(
                            symbol=str(record["symbol"]),
                            bid=str(record["bid"]),
                            ask=str(record["ask"]),
                            bid_size=str(record.get("bid_size", "0")),
                            ask_size=str(record.get("ask_size", "0")),
                            timestamp=str(record["timestamp"]),
                            source=str(record.get("source", "replay")),
                        )
                    )
                elif event_type == "trade":
                    event = self.accept_trade(
                        TradeInput(
                            symbol=str(record["symbol"]),
                            price=str(record["price"]),
                            size=str(record["size"]),
                            timestamp=str(record["timestamp"]),
                            source=str(record.get("source", "replay")),
                        )
                    )
                else:
                    raise ValueError("record type must be quote or trade")
                accepted += 1
                symbols.add(event.symbol)
            except (ValueError, TimeoutError, PermissionError, NotImplementedError, KeyError) as exc:
                rejected += 1
                self._rejections.append(f"record[{index}]: {exc}")

        return self.receipt(
            accepted=accepted,
            rejected=rejected,
            symbol=next(iter(symbols)) if len(symbols) == 1 else None,
        )

    def receipt(
        self,
        *,
        accepted: int | None = None,
        rejected: int | None = None,
        symbol: str | None = None,
    ) -> FeedReceipt:
        accepted_count = len(self._events) if accepted is None else accepted
        rejected_count = len(self._rejections) if rejected is None else rejected
        bid = ask = midpoint = spread = None
        last_price = None

        if self._last_quote:
            bid_d = dec(self._last_quote.payload["bid"], "bid")
            ask_d = dec(self._last_quote.payload["ask"], "ask")
            bid = norm(bid_d)
            ask = norm(ask_d)
            midpoint = norm((bid_d + ask_d) / Decimal("2"))
            spread = norm(ask_d - bid_d)
            symbol = symbol or self._last_quote.symbol

        if self._last_trade:
            last_price = self._last_trade.payload["price"]
            symbol = symbol or self._last_trade.symbol

        status = FeedStatus.ACCEPTED.value
        if rejected_count and not accepted_count:
            if any("stale" in reason for reason in self._rejections):
                status = FeedStatus.REJECTED_STALE.value
            elif any("live mode" in reason or "network transport" in reason for reason in self._rejections):
                status = FeedStatus.REJECTED_LIVE_GATE.value
            else:
                status = FeedStatus.REJECTED_INVALID.value

        core = {
            "schema_version": "v41.0.market_data_receipt.1",
            "version": VERSION,
            "status": status,
            "mode": self.mode,
            "symbol": symbol,
            "accepted_event_count": accepted_count,
            "rejected_event_count": rejected_count,
            "last_price": last_price,
            "bid": bid,
            "ask": ask,
            "midpoint": midpoint,
            "spread": spread,
            "generated_at": utc_now(),
            "network_used": False,
            "rejection_reasons": list(self._rejections),
        }
        return FeedReceipt(**core, snapshot_sha256=canonical_hash(core))

    def export(self, path: Path, receipt: FeedReceipt) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "v41.0.market_data_feed.1",
            "version": VERSION,
            "events": [asdict(event) for event in self._events],
            "receipt": asdict(receipt),
            "network_used": False,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def load_records(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("records")
    if not isinstance(payload, list):
        raise ValueError("input JSON must be a list or contain a records list")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="V41.0 Market Data Feed Foundation")
    parser.add_argument("--action", choices=["demo", "replay", "quote", "trade"], default="demo")
    parser.add_argument("--mode", choices=["replay", "paper", "live"], default="replay")
    parser.add_argument("--enable-live", action="store_true")
    parser.add_argument("--symbol", default="AAPL")
    parser.add_argument("--bid", default="199.90")
    parser.add_argument("--ask", default="200.10")
    parser.add_argument("--bid-size", default="100")
    parser.add_argument("--ask-size", default="120")
    parser.add_argument("--price", default="200")
    parser.add_argument("--size", default="10")
    parser.add_argument("--timestamp")
    parser.add_argument("--reference-time")
    parser.add_argument("--max-age-seconds", type=int, default=60)
    parser.add_argument("--input")
    parser.add_argument(
        "--output",
        default="release/v41/audit/market_data_result_v41_0.json",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    now = args.timestamp or utc_now()
    reference = args.reference_time or now
    feed = MarketDataFeed(
        max_age_seconds=args.max_age_seconds,
        reference_time=reference,
        mode=args.mode,
        enable_live=args.enable_live,
    )

    try:
        if args.action == "replay":
            if not args.input:
                raise ValueError("--input is required for replay")
            receipt = feed.replay(load_records(Path(args.input)))
        elif args.action == "quote":
            feed.accept_quote(
                QuoteInput(
                    symbol=args.symbol,
                    bid=args.bid,
                    ask=args.ask,
                    bid_size=args.bid_size,
                    ask_size=args.ask_size,
                    timestamp=now,
                )
            )
            receipt = feed.receipt()
        elif args.action == "trade":
            feed.accept_trade(
                TradeInput(
                    symbol=args.symbol,
                    price=args.price,
                    size=args.size,
                    timestamp=now,
                )
            )
            receipt = feed.receipt()
        else:
            records = [
                {
                    "type": "quote",
                    "symbol": args.symbol,
                    "bid": args.bid,
                    "ask": args.ask,
                    "bid_size": args.bid_size,
                    "ask_size": args.ask_size,
                    "timestamp": now,
                    "source": "demo",
                },
                {
                    "type": "trade",
                    "symbol": args.symbol,
                    "price": args.price,
                    "size": args.size,
                    "timestamp": now,
                    "source": "demo",
                },
            ]
            receipt = feed.replay(records)

        feed.export(Path(args.output), receipt)
        print(json.dumps(asdict(receipt), indent=2, sort_keys=True))
        return 0 if receipt.status == FeedStatus.ACCEPTED.value else 1
    except (ValueError, TimeoutError, PermissionError, NotImplementedError) as exc:
        feed._rejections.append(str(exc))
        receipt = feed.receipt(accepted=0, rejected=1, symbol=args.symbol.upper())
        feed.export(Path(args.output), receipt)
        print(json.dumps(asdict(receipt), indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
