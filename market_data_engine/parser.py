from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from .models import Bar, MarketDataMessage, Quote, Trade


class MessageParseError(ValueError):
    pass


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        raise MessageParseError("timestamp is required")
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise MessageParseError(f"invalid timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise MessageParseError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def _decimal(value: Any, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise MessageParseError(f"invalid decimal field: {field}") from exc


def _positive_int(value: Any, field: str, *, allow_zero: bool = False) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise MessageParseError(f"invalid integer field: {field}") from exc
    minimum = 0 if allow_zero else 1
    if parsed < minimum:
        raise MessageParseError(f"{field} must be >= {minimum}")
    return parsed


def _sequence(message: dict[str, Any]) -> int | None:
    value = message.get("seq", message.get("sequence"))
    return None if value is None else _positive_int(value, "sequence", allow_zero=True)


class AlpacaMessageParser:
    """Parse Alpaca-style websocket payloads into strongly typed domain models."""

    _ignored_types = {"success", "subscription", "error"}

    def parse_one(self, message: dict[str, Any]) -> MarketDataMessage | None:
        if not isinstance(message, dict):
            raise MessageParseError("message must be an object")
        kind = message.get("T")
        if kind in self._ignored_types:
            return None
        symbol = message.get("S")
        if not isinstance(symbol, str) or not symbol.strip():
            raise MessageParseError("symbol is required")
        symbol = symbol.upper().strip()
        timestamp = _timestamp(message.get("t"))
        sequence = _sequence(message)

        if kind == "q":
            quote = Quote(
                symbol=symbol,
                timestamp=timestamp,
                bid_price=_decimal(message.get("bp"), "bp"),
                bid_size=_positive_int(message.get("bs"), "bs", allow_zero=True),
                ask_price=_decimal(message.get("ap"), "ap"),
                ask_size=_positive_int(message.get("as"), "as", allow_zero=True),
                sequence=sequence,
            )
            if quote.bid_price > quote.ask_price:
                raise MessageParseError("crossed quote rejected")
            return quote

        if kind == "t":
            return Trade(
                symbol=symbol,
                timestamp=timestamp,
                price=_decimal(message.get("p"), "p"),
                size=_positive_int(message.get("s"), "s"),
                exchange=message.get("x"),
                sequence=sequence,
            )

        if kind == "b":
            bar = Bar(
                symbol=symbol,
                timestamp=timestamp,
                open=_decimal(message.get("o"), "o"),
                high=_decimal(message.get("h"), "h"),
                low=_decimal(message.get("l"), "l"),
                close=_decimal(message.get("c"), "c"),
                volume=_positive_int(message.get("v"), "v", allow_zero=True),
                trade_count=None if message.get("n") is None else _positive_int(message.get("n"), "n", allow_zero=True),
                vwap=None if message.get("vw") is None else _decimal(message.get("vw"), "vw"),
                sequence=sequence,
            )
            if bar.low > min(bar.open, bar.close) or bar.high < max(bar.open, bar.close) or bar.low > bar.high:
                raise MessageParseError("invalid OHLC range")
            return bar

        raise MessageParseError(f"unsupported message type: {kind}")

    def parse_frame(self, payload: Any) -> list[MarketDataMessage]:
        messages = payload if isinstance(payload, list) else [payload]
        parsed: list[MarketDataMessage] = []
        for message in messages:
            item = self.parse_one(message)
            if item is not None:
                parsed.append(item)
        return parsed
