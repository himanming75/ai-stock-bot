from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from threading import RLock
from types import MappingProxyType
from typing import Sequence

from broker.contracts_v77_1 import (
    AccountSnapshot,
    BrokerCapabilities,
    BrokerContractError,
    BrokerEnvironment,
    BrokerHealth,
    BrokerOrder,
    BrokerOrderRequest,
    BrokerOrderStatus,
    BrokerSafetyPolicy,
    TERMINAL_ORDER_STATUSES,
    TimeInForce,
    normalize_symbol,
    utc_now,
)


class SandboxBrokerError(BrokerContractError):
    """Raised when an offline sandbox broker operation cannot be completed."""


@dataclass(frozen=True)
class SandboxEvent:
    sequence: int
    event_type: str
    broker_order_id: str | None
    client_order_id: str | None
    occurred_at_utc: datetime
    details: MappingProxyType

    def as_dict(self) -> dict[str, object]:
        return {
            "sequence": self.sequence,
            "event_type": self.event_type,
            "broker_order_id": self.broker_order_id,
            "client_order_id": self.client_order_id,
            "occurred_at_utc": self.occurred_at_utc.isoformat(),
            "details": dict(self.details),
        }


class SandboxBrokerAdapter:
    """Deterministic, memory-only implementation of the V77.1 BrokerContract.

    V77.2 accepts and cancels simulated orders only.  It never opens a socket,
    authenticates a real broker, transmits an order, or creates a fill.
    """

    ADAPTER_NAME = "memory_sandbox_broker_v77_2"

    def __init__(
        self,
        *,
        starting_cash: Decimal = Decimal("100000.00"),
        account_id_masked: str = "SANDBOX-****-0001",
        policy: BrokerSafetyPolicy | None = None,
    ) -> None:
        self._policy = policy or BrokerSafetyPolicy()
        self._policy.validate()
        if self._policy.environment is BrokerEnvironment.LIVE:
            raise SandboxBrokerError("live environment is forbidden")
        if not isinstance(starting_cash, Decimal):
            raise SandboxBrokerError("starting_cash must be Decimal")
        if not starting_cash.is_finite() or starting_cash < 0:
            raise SandboxBrokerError("starting_cash must be finite and non-negative")
        if not account_id_masked.strip():
            raise SandboxBrokerError("account_id_masked is required")

        self._starting_cash = starting_cash
        self._account_id_masked = account_id_masked
        self._orders: dict[str, BrokerOrder] = {}
        self._client_to_broker_id: dict[str, str] = {}
        self._events: list[SandboxEvent] = []
        self._order_sequence = 0
        self._event_sequence = 0
        self._lock = RLock()

        self._capabilities = BrokerCapabilities(
            supports_market_orders=True,
            supports_limit_orders=True,
            supports_stop_orders=True,
            supports_stop_limit_orders=True,
            supports_fractional_quantity=self._policy.allow_fractional_quantity,
            supports_cancel=True,
            supports_replace=False,
            supported_time_in_force=(
                TimeInForce.DAY,
                TimeInForce.GTC,
                TimeInForce.IOC,
            ),
            environment=BrokerEnvironment.OFFLINE,
        )
        self._capabilities.validate()
        self._append_event("adapter_initialized", None, None, {"network_used": "false"})

    @property
    def capabilities(self) -> BrokerCapabilities:
        return self._capabilities

    @property
    def simulated_order_count(self) -> int:
        with self._lock:
            return len(self._orders)

    @property
    def actual_orders_submitted(self) -> int:
        return 0

    def health(self) -> BrokerHealth:
        health = BrokerHealth(
            environment=BrokerEnvironment.OFFLINE,
            adapter_name=self.ADAPTER_NAME,
            connected=False,
            authenticated=False,
            network_used=False,
            checked_at_utc=utc_now(),
            details=MappingProxyType(
                {
                    "mode": "memory_only",
                    "actual_orders_submitted": "0",
                    "simulated_order_count": str(self.simulated_order_count),
                }
            ),
        )
        health.validate(self._policy)
        return health

    def get_account_snapshot(self) -> AccountSnapshot:
        with self._lock:
            open_orders = tuple(
                order
                for order in self._orders.values()
                if order.status not in TERMINAL_ORDER_STATUSES
            )
            snapshot = AccountSnapshot(
                account_id_masked=self._account_id_masked,
                currency="USD",
                cash=self._starting_cash,
                buying_power=self._starting_cash,
                equity=self._starting_cash,
                positions=(),
                open_orders=open_orders,
                captured_at_utc=utc_now(),
            )
        snapshot.validate()
        return snapshot

    def list_orders(self) -> Sequence[BrokerOrder]:
        with self._lock:
            return tuple(self._orders.values())

    def get_order(self, broker_order_id: str) -> BrokerOrder | None:
        with self._lock:
            return self._orders.get(broker_order_id)

    def get_order_by_client_order_id(self, client_order_id: str) -> BrokerOrder | None:
        with self._lock:
            broker_order_id = self._client_to_broker_id.get(client_order_id)
            return self._orders.get(broker_order_id) if broker_order_id else None

    def submit_order(self, request: BrokerOrderRequest) -> BrokerOrder:
        """Accept a simulated order into the memory store.

        This method's name matches BrokerContract.  It does not submit an order
        outside the process, and actual_orders_submitted always remains zero.
        """
        request.validate(self._policy)
        normalized_symbol = normalize_symbol(request.symbol)

        with self._lock:
            client_order_id = request.client_order_id.strip()
            if client_order_id in self._client_to_broker_id:
                existing_id = self._client_to_broker_id[client_order_id]
                self._append_event(
                    "duplicate_order_rejected",
                    existing_id,
                    client_order_id,
                    {"reason": "duplicate_client_order_id"},
                )
                raise SandboxBrokerError(
                    f"duplicate client_order_id: {client_order_id}"
                )

            self._order_sequence += 1
            broker_order_id = f"SBX-V77-2-{self._order_sequence:08d}"
            now = utc_now()
            normalized_request = BrokerOrderRequest(
                client_order_id=client_order_id,
                symbol=normalized_symbol,
                side=request.side,
                quantity=request.quantity,
                order_type=request.order_type,
                time_in_force=request.time_in_force,
                limit_price=request.limit_price,
                stop_price=request.stop_price,
                strategy_id=request.strategy_id.strip(),
                metadata=MappingProxyType(dict(request.metadata)),
            )
            accepted = BrokerOrder(
                broker_order_id=broker_order_id,
                request=normalized_request,
                status=BrokerOrderStatus.ACCEPTED,
                filled_quantity=Decimal("0"),
                average_fill_price=None,
                submitted_at_utc=now,
                updated_at_utc=now,
                rejection_reason=None,
            )
            accepted.validate()
            self._orders[broker_order_id] = accepted
            self._client_to_broker_id[client_order_id] = broker_order_id
            self._append_event(
                "simulated_order_accepted",
                broker_order_id,
                client_order_id,
                {
                    "symbol": normalized_symbol,
                    "side": request.side.value,
                    "quantity": str(request.quantity),
                    "order_type": request.order_type.value,
                },
            )
            return accepted

    def cancel_order(self, broker_order_id: str) -> BrokerOrder:
        with self._lock:
            order = self._orders.get(broker_order_id)
            if order is None:
                raise SandboxBrokerError(f"unknown broker_order_id: {broker_order_id}")
            if order.status in TERMINAL_ORDER_STATUSES:
                raise SandboxBrokerError(
                    f"cannot cancel terminal order: {order.status.value}"
                )

            now = utc_now()
            canceled = BrokerOrder(
                broker_order_id=order.broker_order_id,
                request=order.request,
                status=BrokerOrderStatus.CANCELED,
                filled_quantity=order.filled_quantity,
                average_fill_price=order.average_fill_price,
                submitted_at_utc=order.submitted_at_utc,
                updated_at_utc=now,
                rejection_reason=None,
            )
            canceled.validate()
            self._orders[broker_order_id] = canceled
            self._append_event(
                "simulated_order_canceled",
                broker_order_id,
                order.request.client_order_id,
                {"previous_status": order.status.value},
            )
            return canceled

    def event_ledger(self) -> tuple[SandboxEvent, ...]:
        with self._lock:
            return tuple(self._events)

    def _append_event(
        self,
        event_type: str,
        broker_order_id: str | None,
        client_order_id: str | None,
        details: dict[str, str],
    ) -> None:
        self._event_sequence += 1
        self._events.append(
            SandboxEvent(
                sequence=self._event_sequence,
                event_type=event_type,
                broker_order_id=broker_order_id,
                client_order_id=client_order_id,
                occurred_at_utc=utc_now(),
                details=MappingProxyType(dict(details)),
            )
        )
