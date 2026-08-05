from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ShadowOrder:
    shadow_order_id: str
    strategy_id: str
    symbol: str
    side: str
    notional: Decimal
    reference_price: Decimal
    latency_ms: int
    slippage_bps: Decimal

    def as_json(self) -> dict[str, Any]:
        return {
            "shadow_order_id": self.shadow_order_id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "side": self.side,
            "notional": str(self.notional),
            "reference_price": str(self.reference_price),
            "latency_ms": self.latency_ms,
            "slippage_bps": str(self.slippage_bps),
            "actual_order_created": False,
        }


class ShadowOrderIntake:
    def create(
        self,
        *,
        strategy_id: str,
        symbol: str,
        side: str,
        notional: Decimal,
        reference_price: Decimal,
        latency_ms: int,
        slippage_bps: Decimal,
    ) -> ShadowOrder:
        if side not in {"buy", "sell"}:
            raise ValueError("INVALID_SIDE")
        if notional <= 0 or reference_price <= 0:
            raise ValueError("POSITIVE_VALUES_REQUIRED")
        if latency_ms < 0 or slippage_bps < 0:
            raise ValueError("NON_NEGATIVE_SIMULATION_PARAMETERS_REQUIRED")

        raw = json.dumps(
            {
                "strategy_id": strategy_id,
                "symbol": symbol,
                "side": side,
                "notional": str(notional),
                "reference_price": str(reference_price),
                "latency_ms": latency_ms,
                "slippage_bps": str(slippage_bps),
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        order_id = "shadow-" + hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()[:24]
        return ShadowOrder(
            shadow_order_id=order_id,
            strategy_id=strategy_id,
            symbol=symbol,
            side=side,
            notional=notional,
            reference_price=reference_price,
            latency_ms=latency_ms,
            slippage_bps=slippage_bps,
        )


class FillSimulator:
    def simulate(self, order: ShadowOrder) -> dict[str, Any]:
        direction = Decimal("1") if order.side == "buy" else Decimal("-1")
        slippage_fraction = order.slippage_bps / Decimal("10000")
        fill_price = order.reference_price * (
            Decimal("1") + direction * slippage_fraction
        )
        quantity = order.notional / fill_price
        return {
            "shadow_order_id": order.shadow_order_id,
            "symbol": order.symbol,
            "side": order.side,
            "fill_price": str(fill_price.quantize(Decimal("0.0001"))),
            "quantity": str(quantity.quantize(Decimal("0.000001"))),
            "simulated_latency_ms": order.latency_ms,
            "simulated_slippage_bps": str(order.slippage_bps),
            "fill_state": "FILLED_SHADOW",
            "actual_fill_received": False,
            "actual_broker_event_used": False,
        }


class ShadowLedger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, value: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(value, sort_keys=True) + "\n")
