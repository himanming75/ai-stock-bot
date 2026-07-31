from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from threading import RLock
from types import MappingProxyType

from broker.contracts_v77_1 import (
    AccountSnapshot,
    BrokerOrder,
    BrokerOrderStatus,
    BrokerPosition,
    OrderSide,
    TERMINAL_ORDER_STATUSES,
    utc_now,
)
from broker.sandbox_adapter_v77_2 import (
    SandboxBrokerAdapter,
    SandboxBrokerError,
)


@dataclass(frozen=True)
class SandboxFill:
    fill_id: str
    broker_order_id: str
    quantity: Decimal
    price: Decimal
    cumulative_quantity: Decimal
    cumulative_average_price: Decimal
    occurred_at_utc: object

    def as_dict(self) -> dict[str, str]:
        return {
            "fill_id": self.fill_id,
            "broker_order_id": self.broker_order_id,
            "quantity": str(self.quantity),
            "price": str(self.price),
            "cumulative_quantity": str(self.cumulative_quantity),
            "cumulative_average_price": str(self.cumulative_average_price),
            "occurred_at_utc": self.occurred_at_utc.isoformat(),
        }


@dataclass
class _PositionState:
    quantity: Decimal
    average_entry_price: Decimal
    last_price: Decimal


class OrderLifecycleSimulator(SandboxBrokerAdapter):
    """Offline order lifecycle simulator layered on the V77.2 adapter.

    The simulator mutates only in-process cash, position, order, fill, and event
    state.  It never opens a network connection or submits a real broker order.
    """

    ADAPTER_NAME = "memory_order_lifecycle_simulator_v77_3"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._cash = self._starting_cash
        self._positions: dict[str, _PositionState] = {}
        self._fills: list[SandboxFill] = []
        self._fill_sequence = 0
        self._lifecycle_lock = RLock()

    @property
    def simulated_fill_count(self) -> int:
        with self._lifecycle_lock:
            return len(self._fills)

    def list_fills(self) -> tuple[SandboxFill, ...]:
        with self._lifecycle_lock:
            return tuple(self._fills)

    def apply_fill(
        self,
        broker_order_id: str,
        *,
        quantity: Decimal,
        price: Decimal,
    ) -> BrokerOrder:
        if not isinstance(quantity, Decimal) or not quantity.is_finite() or quantity <= 0:
            raise SandboxBrokerError("fill quantity must be finite Decimal greater than zero")
        if not isinstance(price, Decimal) or not price.is_finite() or price <= 0:
            raise SandboxBrokerError("fill price must be finite Decimal greater than zero")

        with self._lifecycle_lock, self._lock:
            order = self._orders.get(broker_order_id)
            if order is None:
                raise SandboxBrokerError(f"unknown broker_order_id: {broker_order_id}")
            if order.status in TERMINAL_ORDER_STATUSES:
                raise SandboxBrokerError(
                    f"cannot fill terminal order: {order.status.value}"
                )
            if order.status not in {
                BrokerOrderStatus.ACCEPTED,
                BrokerOrderStatus.PARTIALLY_FILLED,
            }:
                raise SandboxBrokerError(
                    f"order status cannot receive fill: {order.status.value}"
                )

            remaining = order.request.quantity - order.filled_quantity
            if quantity > remaining:
                raise SandboxBrokerError("fill quantity exceeds remaining order quantity")

            trade_value = quantity * price
            symbol = order.request.symbol
            if order.request.side is OrderSide.BUY:
                if trade_value > self._cash:
                    raise SandboxBrokerError("insufficient sandbox cash")
                self._cash -= trade_value
                self._apply_buy(symbol, quantity, price)
            else:
                self._apply_sell(symbol, quantity, price)
                self._cash += trade_value

            previous_value = (
                order.filled_quantity * order.average_fill_price
                if order.average_fill_price is not None
                else Decimal("0")
            )
            cumulative_quantity = order.filled_quantity + quantity
            cumulative_average = (
                previous_value + trade_value
            ) / cumulative_quantity
            status = (
                BrokerOrderStatus.FILLED
                if cumulative_quantity == order.request.quantity
                else BrokerOrderStatus.PARTIALLY_FILLED
            )
            now = utc_now()
            updated = BrokerOrder(
                broker_order_id=order.broker_order_id,
                request=order.request,
                status=status,
                filled_quantity=cumulative_quantity,
                average_fill_price=cumulative_average,
                submitted_at_utc=order.submitted_at_utc,
                updated_at_utc=now,
                rejection_reason=None,
            )
            updated.validate()
            self._orders[broker_order_id] = updated

            self._fill_sequence += 1
            fill = SandboxFill(
                fill_id=f"FILL-V77-3-{self._fill_sequence:08d}",
                broker_order_id=broker_order_id,
                quantity=quantity,
                price=price,
                cumulative_quantity=cumulative_quantity,
                cumulative_average_price=cumulative_average,
                occurred_at_utc=now,
            )
            self._fills.append(fill)
            self._append_event(
                "simulated_partial_fill"
                if status is BrokerOrderStatus.PARTIALLY_FILLED
                else "simulated_full_fill",
                broker_order_id,
                order.request.client_order_id,
                {
                    "fill_id": fill.fill_id,
                    "fill_quantity": str(quantity),
                    "fill_price": str(price),
                    "cumulative_quantity": str(cumulative_quantity),
                    "average_fill_price": str(cumulative_average),
                    "cash_after": str(self._cash),
                },
            )
            return updated

    def get_account_snapshot(self) -> AccountSnapshot:
        with self._lifecycle_lock, self._lock:
            positions = tuple(
                self._to_contract_position(symbol, state)
                for symbol, state in sorted(self._positions.items())
                if state.quantity != 0
            )
            open_orders = tuple(
                order
                for order in self._orders.values()
                if order.status not in TERMINAL_ORDER_STATUSES
            )
            market_value = sum(
                (position.market_value for position in positions),
                Decimal("0"),
            )
            snapshot = AccountSnapshot(
                account_id_masked=self._account_id_masked,
                currency="USD",
                cash=self._cash,
                buying_power=self._cash,
                equity=self._cash + market_value,
                positions=positions,
                open_orders=open_orders,
                captured_at_utc=utc_now(),
            )
        snapshot.validate()
        return snapshot

    def _apply_buy(self, symbol: str, quantity: Decimal, price: Decimal) -> None:
        current = self._positions.get(symbol)
        if current is None:
            self._positions[symbol] = _PositionState(quantity, price, price)
            return
        total_quantity = current.quantity + quantity
        total_cost = current.quantity * current.average_entry_price + quantity * price
        current.quantity = total_quantity
        current.average_entry_price = total_cost / total_quantity
        current.last_price = price

    def _apply_sell(self, symbol: str, quantity: Decimal, price: Decimal) -> None:
        current = self._positions.get(symbol)
        if current is None or current.quantity < quantity:
            raise SandboxBrokerError("insufficient sandbox position")
        current.quantity -= quantity
        current.last_price = price
        if current.quantity == 0:
            del self._positions[symbol]

    @staticmethod
    def _to_contract_position(
        symbol: str,
        state: _PositionState,
    ) -> BrokerPosition:
        market_value = state.quantity * state.last_price
        unrealized_pnl = (
            state.last_price - state.average_entry_price
        ) * state.quantity
        position = BrokerPosition(
            symbol=symbol,
            quantity=state.quantity,
            average_entry_price=state.average_entry_price,
            market_value=market_value,
            unrealized_pnl=unrealized_pnl,
        )
        position.validate()
        return position
