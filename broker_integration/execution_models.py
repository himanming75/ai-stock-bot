from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
import hashlib
import json
import re


VALID_SIDES = {"buy", "sell"}
VALID_TYPES = {"market", "limit"}
VALID_TIF = {"day", "gtc"}
CLIENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,48}$")


@dataclass(frozen=True)
class CanonicalOrderRequest:
    symbol: str
    side: str
    order_type: str
    time_in_force: str
    qty: Decimal | None = None
    notional: Decimal | None = None
    limit_price: Decimal | None = None
    client_order_id: str = ""

    def validate(self) -> None:
        symbol = self.symbol.strip().upper()
        if not symbol or not symbol.replace(".", "").isalnum():
            raise ValueError("INVALID_SYMBOL")
        if self.side not in VALID_SIDES:
            raise ValueError("INVALID_SIDE")
        if self.order_type not in VALID_TYPES:
            raise ValueError("INVALID_ORDER_TYPE")
        if self.time_in_force not in VALID_TIF:
            raise ValueError("INVALID_TIME_IN_FORCE")
        if (self.qty is None) == (self.notional is None):
            raise ValueError("EXACTLY_ONE_OF_QTY_OR_NOTIONAL_REQUIRED")
        if self.qty is not None and self.qty <= 0:
            raise ValueError("QTY_MUST_BE_POSITIVE")
        if self.notional is not None and self.notional <= 0:
            raise ValueError("NOTIONAL_MUST_BE_POSITIVE")

        if self.notional is not None:
            if self.order_type != "market":
                raise ValueError("NOTIONAL_ONLY_ALLOWED_FOR_MARKET_ORDER")
            if self.side != "buy":
                raise ValueError("NOTIONAL_SELL_NOT_ALLOWED_BY_P2_POLICY")

        if self.order_type == "limit":
            if self.limit_price is None or self.limit_price <= 0:
                raise ValueError("LIMIT_PRICE_REQUIRED")
            if self.notional is not None:
                raise ValueError("NOTIONAL_LIMIT_ORDER_NOT_ALLOWED")
            if self.qty is not None and self.qty != self.qty.to_integral_value():
                raise ValueError("FRACTIONAL_QTY_LIMIT_ORDER_NOT_ALLOWED")
        elif self.limit_price is not None:
            raise ValueError("LIMIT_PRICE_NOT_ALLOWED_FOR_MARKET_ORDER")

        if not CLIENT_ID_PATTERN.match(self.client_order_id):
            raise ValueError("INVALID_CLIENT_ORDER_ID")

    def as_payload(self) -> dict[str, Any]:
        self.validate()
        payload: dict[str, Any] = {
            "symbol": self.symbol.strip().upper(),
            "side": self.side,
            "type": self.order_type,
            "time_in_force": self.time_in_force,
            "client_order_id": self.client_order_id,
        }
        if self.qty is not None:
            payload["qty"] = format(self.qty, "f")
        if self.notional is not None:
            payload["notional"] = format(self.notional, "f")
        if self.limit_price is not None:
            payload["limit_price"] = format(self.limit_price, "f")
        return payload


def canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def order_request_hash(order: CanonicalOrderRequest) -> str:
    return canonical_hash(order.as_payload())
