#!/usr/bin/env python3
"""
V32.0 Broker Adapter Layer

Safe broker abstraction layer with no live network transport.

Includes:
- Common broker adapter protocol
- Broker capabilities model
- Account snapshot / position / order models
- PaperBrokerAdapter with deterministic in-memory fills
- Disabled external adapters for IBKR, Alpaca, and TradeStation
- Adapter registry and factory
- Health check and capability inspection
- Order submission guard that rejects unsupported live routing

No API keys are accepted and no external network requests are performed.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, Sequence


VERSION = "32.0"


class BrokerName(str, Enum):
    PAPER = "paper"
    IBKR = "ibkr"
    ALPACA = "alpaca"
    TRADESTATION = "tradestation"


class TradingMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class OrderStatus(str, Enum):
    ACCEPTED = "accepted"
    FILLED = "filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class BrokerCapabilities:
    supports_paper: bool
    supports_live: bool
    supports_market_orders: bool
    supports_limit_orders: bool
    supports_fractional_shares: bool
    supports_short_selling: bool
    supports_cancel: bool
    network_transport_enabled: bool


@dataclass(frozen=True)
class BrokerHealth:
    broker: str
    status: str
    connected: bool
    authenticated: bool
    mode: str
    network_transport_enabled: bool
    message: str


@dataclass(frozen=True)
class Position:
    symbol: str
    quantity: str
    average_price: str
    market_price: str
    market_value: str
    unrealized_pnl: str


@dataclass(frozen=True)
class AccountSnapshot:
    broker: str
    mode: str
    account_id: str
    cash: str
    equity: str
    buying_power: str
    positions: list[Position]
    generated_at: str


@dataclass(frozen=True)
class BrokerOrder:
    symbol: str
    side: OrderSide
    quantity: str
    order_type: OrderType
    limit_price: str | None = None
    client_order_id: str | None = None


@dataclass(frozen=True)
class OrderResult:
    broker: str
    broker_order_id: str | None
    client_order_id: str
    status: str
    mode: str
    symbol: str
    side: str
    quantity: str
    filled_quantity: str
    average_fill_price: str | None
    rejection_reason: str | None
    generated_at: str
    live_transport_used: bool


class BrokerAdapter(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def mode(self) -> TradingMode: ...

    def capabilities(self) -> BrokerCapabilities: ...

    def health_check(self) -> BrokerHealth: ...

    def account_snapshot(self) -> AccountSnapshot: ...

    def submit_order(self, order: BrokerOrder) -> OrderResult: ...

    def cancel_order(self, broker_order_id: str) -> OrderResult: ...


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_positive_decimal(value: str, field_name: str) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError(f"{field_name} must be greater than zero")
    return number


def normalize_decimal(value: Decimal) -> str:
    return format(value.normalize(), "f")


class PaperBrokerAdapter:
    """Deterministic in-memory paper broker."""

    def __init__(
        self,
        starting_cash: str = "100000",
        market_prices: dict[str, str] | None = None,
    ) -> None:
        self._mode = TradingMode.PAPER
        self._cash = parse_positive_decimal(starting_cash, "starting_cash")
        self._market_prices = {
            key.upper(): parse_positive_decimal(value, f"price[{key}]")
            for key, value in (market_prices or {
                "AAPL": "200",
                "MSFT": "450",
                "NVDA": "120",
                "SPY": "600",
            }).items()
        }
        self._positions: dict[str, dict[str, Decimal]] = {}
        self._orders: dict[str, OrderResult] = {}

    @property
    def name(self) -> str:
        return BrokerName.PAPER.value

    @property
    def mode(self) -> TradingMode:
        return self._mode

    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            supports_paper=True,
            supports_live=False,
            supports_market_orders=True,
            supports_limit_orders=True,
            supports_fractional_shares=True,
            supports_short_selling=False,
            supports_cancel=True,
            network_transport_enabled=False,
        )

    def health_check(self) -> BrokerHealth:
        return BrokerHealth(
            broker=self.name,
            status="PASS",
            connected=True,
            authenticated=True,
            mode=self.mode.value,
            network_transport_enabled=False,
            message="In-memory paper broker is ready.",
        )

    def _price_for(self, symbol: str) -> Decimal:
        symbol = symbol.upper()
        if symbol not in self._market_prices:
            raise ValueError(f"No simulated market price configured for {symbol}")
        return self._market_prices[symbol]

    def account_snapshot(self) -> AccountSnapshot:
        positions: list[Position] = []
        market_value_total = Decimal("0")

        for symbol in sorted(self._positions):
            data = self._positions[symbol]
            quantity = data["quantity"]
            average_price = data["average_price"]
            market_price = self._price_for(symbol)
            market_value = quantity * market_price
            unrealized = (market_price - average_price) * quantity
            market_value_total += market_value
            positions.append(Position(
                symbol=symbol,
                quantity=normalize_decimal(quantity),
                average_price=normalize_decimal(average_price),
                market_price=normalize_decimal(market_price),
                market_value=normalize_decimal(market_value),
                unrealized_pnl=normalize_decimal(unrealized),
            ))

        equity = self._cash + market_value_total
        return AccountSnapshot(
            broker=self.name,
            mode=self.mode.value,
            account_id="paper-v32",
            cash=normalize_decimal(self._cash),
            equity=normalize_decimal(equity),
            buying_power=normalize_decimal(self._cash),
            positions=positions,
            generated_at=utc_now(),
        )

    def submit_order(self, order: BrokerOrder) -> OrderResult:
        symbol = order.symbol.strip().upper()
        quantity = parse_positive_decimal(order.quantity, "quantity")
        client_order_id = (
            order.client_order_id.strip()
            if order.client_order_id
            else f"v32-{uuid.uuid4().hex[:20]}"
        )
        market_price = self._price_for(symbol)

        if order.order_type == OrderType.LIMIT:
            if order.limit_price is None:
                return self._rejected(
                    order, client_order_id, "limit_price is required"
                )
            limit_price = parse_positive_decimal(
                order.limit_price, "limit_price"
            )
            if order.side == OrderSide.BUY and limit_price < market_price:
                return self._accepted_unfilled(order, client_order_id)
            if order.side == OrderSide.SELL and limit_price > market_price:
                return self._accepted_unfilled(order, client_order_id)

        cost = quantity * market_price
        if order.side == OrderSide.BUY:
            if cost > self._cash:
                return self._rejected(
                    order, client_order_id, "insufficient buying power"
                )
            current = self._positions.get(symbol)
            if current:
                old_qty = current["quantity"]
                old_avg = current["average_price"]
                new_qty = old_qty + quantity
                new_avg = ((old_qty * old_avg) + cost) / new_qty
                current["quantity"] = new_qty
                current["average_price"] = new_avg
            else:
                self._positions[symbol] = {
                    "quantity": quantity,
                    "average_price": market_price,
                }
            self._cash -= cost
        else:
            current = self._positions.get(symbol)
            if current is None or current["quantity"] < quantity:
                return self._rejected(
                    order,
                    client_order_id,
                    "short selling is disabled and position is insufficient",
                )
            current["quantity"] -= quantity
            self._cash += cost
            if current["quantity"] == 0:
                del self._positions[symbol]

        broker_order_id = f"paper-{uuid.uuid4().hex}"
        result = OrderResult(
            broker=self.name,
            broker_order_id=broker_order_id,
            client_order_id=client_order_id,
            status=OrderStatus.FILLED.value,
            mode=self.mode.value,
            symbol=symbol,
            side=order.side.value,
            quantity=normalize_decimal(quantity),
            filled_quantity=normalize_decimal(quantity),
            average_fill_price=normalize_decimal(market_price),
            rejection_reason=None,
            generated_at=utc_now(),
            live_transport_used=False,
        )
        self._orders[broker_order_id] = result
        return result

    def _accepted_unfilled(
        self,
        order: BrokerOrder,
        client_order_id: str,
    ) -> OrderResult:
        broker_order_id = f"paper-{uuid.uuid4().hex}"
        result = OrderResult(
            broker=self.name,
            broker_order_id=broker_order_id,
            client_order_id=client_order_id,
            status=OrderStatus.ACCEPTED.value,
            mode=self.mode.value,
            symbol=order.symbol.upper(),
            side=order.side.value,
            quantity=order.quantity,
            filled_quantity="0",
            average_fill_price=None,
            rejection_reason=None,
            generated_at=utc_now(),
            live_transport_used=False,
        )
        self._orders[broker_order_id] = result
        return result

    def _rejected(
        self,
        order: BrokerOrder,
        client_order_id: str,
        reason: str,
    ) -> OrderResult:
        return OrderResult(
            broker=self.name,
            broker_order_id=None,
            client_order_id=client_order_id,
            status=OrderStatus.REJECTED.value,
            mode=self.mode.value,
            symbol=order.symbol.upper(),
            side=order.side.value,
            quantity=order.quantity,
            filled_quantity="0",
            average_fill_price=None,
            rejection_reason=reason,
            generated_at=utc_now(),
            live_transport_used=False,
        )

    def cancel_order(self, broker_order_id: str) -> OrderResult:
        existing = self._orders.get(broker_order_id)
        if existing is None:
            return OrderResult(
                broker=self.name,
                broker_order_id=broker_order_id,
                client_order_id="unknown",
                status=OrderStatus.REJECTED.value,
                mode=self.mode.value,
                symbol="UNKNOWN",
                side="unknown",
                quantity="0",
                filled_quantity="0",
                average_fill_price=None,
                rejection_reason="order not found",
                generated_at=utc_now(),
                live_transport_used=False,
            )
        if existing.status == OrderStatus.FILLED.value:
            return OrderResult(
                **{
                    **asdict(existing),
                    "status": OrderStatus.REJECTED.value,
                    "rejection_reason": "filled orders cannot be cancelled",
                    "generated_at": utc_now(),
                }
            )
        cancelled = OrderResult(
            **{
                **asdict(existing),
                "status": OrderStatus.CANCELLED.value,
                "rejection_reason": None,
                "generated_at": utc_now(),
            }
        )
        self._orders[broker_order_id] = cancelled
        return cancelled


class DisabledExternalBrokerAdapter:
    """Metadata-only adapter for a future external broker integration."""

    def __init__(self, broker: BrokerName, mode: TradingMode) -> None:
        if broker == BrokerName.PAPER:
            raise ValueError("Use PaperBrokerAdapter for paper broker")
        self._broker = broker
        self._mode = mode

    @property
    def name(self) -> str:
        return self._broker.value

    @property
    def mode(self) -> TradingMode:
        return self._mode

    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            supports_paper=True,
            supports_live=True,
            supports_market_orders=True,
            supports_limit_orders=True,
            supports_fractional_shares=self._broker == BrokerName.ALPACA,
            supports_short_selling=True,
            supports_cancel=True,
            network_transport_enabled=False,
        )

    def health_check(self) -> BrokerHealth:
        return BrokerHealth(
            broker=self.name,
            status="DISABLED",
            connected=False,
            authenticated=False,
            mode=self.mode.value,
            network_transport_enabled=False,
            message=(
                f"{self.name} adapter contract exists, but network transport "
                "and credential handling are disabled in V32.0."
            ),
        )

    def account_snapshot(self) -> AccountSnapshot:
        raise RuntimeError(
            f"{self.name} account transport is not implemented in V32.0"
        )

    def submit_order(self, order: BrokerOrder) -> OrderResult:
        return OrderResult(
            broker=self.name,
            broker_order_id=None,
            client_order_id=order.client_order_id or "not-submitted",
            status=OrderStatus.REJECTED.value,
            mode=self.mode.value,
            symbol=order.symbol.upper(),
            side=order.side.value,
            quantity=order.quantity,
            filled_quantity="0",
            average_fill_price=None,
            rejection_reason=(
                f"{self.name} network transport is disabled in V32.0"
            ),
            generated_at=utc_now(),
            live_transport_used=False,
        )

    def cancel_order(self, broker_order_id: str) -> OrderResult:
        return OrderResult(
            broker=self.name,
            broker_order_id=broker_order_id,
            client_order_id="not-submitted",
            status=OrderStatus.REJECTED.value,
            mode=self.mode.value,
            symbol="UNKNOWN",
            side="unknown",
            quantity="0",
            filled_quantity="0",
            average_fill_price=None,
            rejection_reason=(
                f"{self.name} network transport is disabled in V32.0"
            ),
            generated_at=utc_now(),
            live_transport_used=False,
        )


def create_adapter(
    broker: BrokerName,
    mode: TradingMode,
) -> BrokerAdapter:
    if broker == BrokerName.PAPER:
        if mode != TradingMode.PAPER:
            raise ValueError("paper adapter only supports paper mode")
        return PaperBrokerAdapter()
    return DisabledExternalBrokerAdapter(broker, mode)


def registry_snapshot() -> dict[str, Any]:
    items = {}
    for broker in BrokerName:
        mode = TradingMode.PAPER if broker == BrokerName.PAPER else TradingMode.LIVE
        adapter = create_adapter(broker, mode)
        items[broker.value] = {
            "health": asdict(adapter.health_check()),
            "capabilities": asdict(adapter.capabilities()),
        }
    return {
        "schema_version": "v32.0.broker_registry.1",
        "version": VERSION,
        "brokers": items,
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="V32.0 Broker Adapter Layer")
    p.add_argument(
        "--broker",
        choices=[item.value for item in BrokerName],
        default="paper",
    )
    p.add_argument(
        "--mode",
        choices=[item.value for item in TradingMode],
        default="paper",
    )
    p.add_argument(
        "--action",
        choices=["health", "registry", "account", "order"],
        default="registry",
    )
    p.add_argument("--symbol", default="AAPL")
    p.add_argument("--side", choices=[item.value for item in OrderSide], default="buy")
    p.add_argument("--quantity", default="1")
    p.add_argument(
        "--order-type",
        choices=[item.value for item in OrderType],
        default="market",
    )
    p.add_argument("--limit-price", default=None)
    p.add_argument(
        "--output",
        default="release/v32/audit/broker_adapter_result_v32_0.json",
    )
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    broker = BrokerName(args.broker)
    mode = TradingMode(args.mode)

    try:
        adapter = create_adapter(broker, mode)
        if args.action == "registry":
            payload: Any = registry_snapshot()
            success = True
        elif args.action == "health":
            payload = asdict(adapter.health_check())
            success = True
        elif args.action == "account":
            payload = asdict(adapter.account_snapshot())
            success = True
        else:
            order = BrokerOrder(
                symbol=args.symbol,
                side=OrderSide(args.side),
                quantity=args.quantity,
                order_type=OrderType(args.order_type),
                limit_price=args.limit_price,
            )
            result = adapter.submit_order(order)
            payload = asdict(result)
            success = result.status != OrderStatus.REJECTED.value
    except Exception as exc:
        payload = {
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
        }
        success = False

    output = Path(args.output)
    write_json(output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
