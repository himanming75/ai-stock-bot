from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
import re
from typing import Any

VALID_SIDES = {"buy", "sell"}
VALID_TYPES = {"market", "limit"}
VALID_TIF = {"day"}
CLIENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,48}$")


@dataclass(frozen=True)
class LiveMicroOrder:
    symbol: str
    side: str
    order_type: str
    time_in_force: str
    client_order_id: str
    qty: Decimal | None = None
    notional: Decimal | None = None
    limit_price: Decimal | None = None

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
        if not CLIENT_ID_PATTERN.match(self.client_order_id):
            raise ValueError("INVALID_CLIENT_ORDER_ID")
        if (self.qty is None) == (self.notional is None):
            raise ValueError("EXACTLY_ONE_OF_QTY_OR_NOTIONAL_REQUIRED")
        if self.qty is not None and self.qty <= 0:
            raise ValueError("QTY_MUST_BE_POSITIVE")
        if self.notional is not None and self.notional <= 0:
            raise ValueError("NOTIONAL_MUST_BE_POSITIVE")
        if self.notional is not None:
            if self.order_type != "market":
                raise ValueError("NOTIONAL_ONLY_FOR_MARKET")
            if self.side != "buy":
                raise ValueError("NOTIONAL_SELL_REJECTED")
        if self.order_type == "limit":
            if self.limit_price is None or self.limit_price <= 0:
                raise ValueError("LIMIT_PRICE_REQUIRED")
            if self.qty is None:
                raise ValueError("LIMIT_QTY_REQUIRED")
        elif self.limit_price is not None:
            raise ValueError("LIMIT_PRICE_NOT_ALLOWED")

    def payload(self) -> dict[str, Any]:
        self.validate()
        value: dict[str, Any] = {
            "symbol": self.symbol.strip().upper(),
            "side": self.side,
            "type": self.order_type,
            "time_in_force": self.time_in_force,
            "client_order_id": self.client_order_id,
        }
        if self.qty is not None:
            value["qty"] = format(self.qty, "f")
        if self.notional is not None:
            value["notional"] = format(self.notional, "f")
        if self.limit_price is not None:
            value["limit_price"] = format(self.limit_price, "f")
        return value


def canonical_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
