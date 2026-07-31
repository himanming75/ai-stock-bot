from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from types import MappingProxyType

from broker.broker_state_checkpoint_v77_5 import (
    BrokerStateCheckpoint,
    BrokerStateCheckpointManager,
    CheckpointError,
)
from broker.contracts_v77_1 import (
    BrokerOrder,
    BrokerOrderRequest,
    BrokerOrderStatus,
    OrderSide,
    OrderType,
    TimeInForce,
)
from broker.execution_event_reconciliation_v77_4 import (
    ExecutionEventReconciler,
    ReconciliationReport,
)
from broker.order_lifecycle_simulator_v77_3 import (
    OrderLifecycleSimulator,
    SandboxFill,
    _PositionState,
)
from broker.sandbox_adapter_v77_2 import SandboxEvent


class RecoveryError(ValueError):
    """Raised when checkpoint recovery or replay verification fails."""


class RestartRecoveryReplay:
    """Restore an offline simulator from a verified V77.5 checkpoint."""

    def __init__(
        self,
        *,
        checkpoint_manager: BrokerStateCheckpointManager | None = None,
        reconciler: ExecutionEventReconciler | None = None,
    ) -> None:
        self._checkpoint_manager = checkpoint_manager or BrokerStateCheckpointManager()
        self._reconciler = reconciler or ExecutionEventReconciler()

    def restore(
        self,
        checkpoint: BrokerStateCheckpoint,
    ) -> OrderLifecycleSimulator:
        if not self._checkpoint_manager.verify(checkpoint):
            raise RecoveryError("checkpoint integrity verification failed")

        simulator = OrderLifecycleSimulator(
            starting_cash=Decimal(checkpoint.starting_cash)
        )

        with simulator._lifecycle_lock, simulator._lock:
            simulator._cash = Decimal(checkpoint.cash)
            simulator._orders.clear()
            simulator._client_to_broker_id.clear()
            simulator._positions.clear()
            simulator._fills.clear()
            simulator._events.clear()

            for position in checkpoint.positions:
                simulator._positions[str(position["symbol"])] = _PositionState(
                    quantity=Decimal(str(position["quantity"])),
                    average_entry_price=Decimal(
                        str(position["average_entry_price"])
                    ),
                    last_price=self._derive_last_price(position),
                )

            max_order_sequence = 0
            for item in checkpoint.orders:
                request = BrokerOrderRequest(
                    client_order_id=str(item["client_order_id"]),
                    symbol=str(item["symbol"]),
                    side=OrderSide(str(item["side"])),
                    quantity=Decimal(str(item["quantity"])),
                    order_type=self._derive_order_type(item),
                    time_in_force=self._derive_time_in_force(item),
                )
                order = BrokerOrder(
                    broker_order_id=str(item["broker_order_id"]),
                    request=request,
                    status=BrokerOrderStatus(str(item["status"])),
                    filled_quantity=Decimal(str(item["filled_quantity"])),
                    average_fill_price=(
                        Decimal(str(item["average_fill_price"]))
                        if item["average_fill_price"] is not None
                        else None
                    ),
                    submitted_at_utc=datetime.fromisoformat(
                        str(item["submitted_at_utc"])
                    ),
                    updated_at_utc=datetime.fromisoformat(
                        str(item["updated_at_utc"])
                    ),
                    rejection_reason=None,
                )
                order.validate()
                simulator._orders[order.broker_order_id] = order
                simulator._client_to_broker_id[
                    order.request.client_order_id
                ] = order.broker_order_id
                max_order_sequence = max(
                    max_order_sequence,
                    self._numeric_suffix(order.broker_order_id),
                )

            max_fill_sequence = 0
            for item in checkpoint.fills:
                fill = SandboxFill(
                    fill_id=str(item["fill_id"]),
                    broker_order_id=str(item["broker_order_id"]),
                    quantity=Decimal(str(item["quantity"])),
                    price=Decimal(str(item["price"])),
                    cumulative_quantity=Decimal(
                        str(item["cumulative_quantity"])
                    ),
                    cumulative_average_price=Decimal(
                        str(item["cumulative_average_price"])
                    ),
                    occurred_at_utc=datetime.fromisoformat(
                        str(item["occurred_at_utc"])
                    ),
                )
                simulator._fills.append(fill)
                max_fill_sequence = max(
                    max_fill_sequence,
                    self._numeric_suffix(fill.fill_id),
                )

            max_event_sequence = 0
            for item in checkpoint.events:
                event = SandboxEvent(
                    sequence=int(item["sequence"]),
                    event_type=str(item["event_type"]),
                    broker_order_id=(
                        str(item["broker_order_id"])
                        if item["broker_order_id"] is not None
                        else None
                    ),
                    client_order_id=(
                        str(item["client_order_id"])
                        if item["client_order_id"] is not None
                        else None
                    ),
                    occurred_at_utc=datetime.fromisoformat(
                        str(item["occurred_at_utc"])
                    ),
                    details=MappingProxyType(dict(item["details"])),
                )
                simulator._events.append(event)
                max_event_sequence = max(max_event_sequence, event.sequence)

            simulator._order_sequence = max_order_sequence
            simulator._fill_sequence = max_fill_sequence
            simulator._event_sequence = max_event_sequence

        report = self._reconciler.reconcile(simulator)
        if not report.passed:
            raise RecoveryError(
                f"recovered state reconciliation failed: {report.issue_count}"
            )
        return simulator

    def verify_replay(
        self,
        checkpoint: BrokerStateCheckpoint,
        simulator: OrderLifecycleSimulator,
    ) -> dict[str, object]:
        report = self._reconciler.reconcile(simulator)
        replayed = self._checkpoint_manager.create(
            simulator,
            checkpoint_id=checkpoint.checkpoint_id,
        )
        checks = {
            "reconciliation_pass": report.passed,
            "state_sha256_match": replayed.state_sha256 == checkpoint.state_sha256,
            "cash_match": replayed.cash == checkpoint.cash,
            "positions_match": replayed.positions == checkpoint.positions,
            "orders_match": replayed.orders == checkpoint.orders,
            "fills_match": replayed.fills == checkpoint.fills,
            "events_match": replayed.events == checkpoint.events,
            "order_ids_match": [
                item["broker_order_id"] for item in replayed.orders
            ] == [
                item["broker_order_id"] for item in checkpoint.orders
            ],
            "fill_ids_match": [
                item["fill_id"] for item in replayed.fills
            ] == [
                item["fill_id"] for item in checkpoint.fills
            ],
            "event_sequences_match": [
                item["sequence"] for item in replayed.events
            ] == [
                item["sequence"] for item in checkpoint.events
            ],
        }
        return {
            "status": "PASS" if all(checks.values()) else "FAIL",
            "checks": checks,
            "reconciliation": report.as_dict(),
            "replayed_state_sha256": replayed.state_sha256,
            "source_state_sha256": checkpoint.state_sha256,
        }

    @staticmethod
    def _derive_last_price(position: MappingProxyType) -> Decimal:
        quantity = Decimal(str(position["quantity"]))
        market_value = Decimal(str(position["market_value"]))
        if quantity == 0:
            raise RecoveryError("zero-quantity checkpoint position is invalid")
        return market_value / quantity

    @staticmethod
    def _derive_order_type(item: MappingProxyType) -> OrderType:
        # V77.5 checkpoints did not persist the original order type.  Recovery
        # selects a contract-valid placeholder because reconciliation and replay
        # identity depend on execution state, not routing semantics.
        return OrderType.MARKET

    @staticmethod
    def _derive_time_in_force(item: MappingProxyType) -> TimeInForce:
        return TimeInForce.DAY

    @staticmethod
    def _numeric_suffix(value: str) -> int:
        try:
            return int(value.rsplit("-", 1)[-1])
        except ValueError:
            return 0
