from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Any

from broker.broker_state_checkpoint_v77_5 import (
    BrokerStateCheckpoint,
    BrokerStateCheckpointManager,
)
from broker.contracts_v77_1 import (
    BrokerOrderRequest,
    OrderSide,
    OrderType,
    TimeInForce,
)
from broker.execution_event_reconciliation_v77_4 import ExecutionEventReconciler
from broker.order_lifecycle_simulator_v77_3 import OrderLifecycleSimulator
from broker.restart_recovery_replay_v77_6 import RestartRecoveryReplay


class ContinuationSafetyError(ValueError):
    """Raised when post-recovery continuation safety cannot be proven."""


@dataclass(frozen=True)
class ContinuationSafetyReport:
    status: str
    checks: MappingProxyType
    source_checkpoint_sha256: str
    continued_checkpoint_sha256: str
    source_order_count: int
    continued_order_count: int
    source_fill_count: int
    continued_fill_count: int
    source_event_count: int
    continued_event_count: int
    new_order_id: str
    new_fill_id: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "checks": dict(self.checks),
            "source_checkpoint_sha256": self.source_checkpoint_sha256,
            "continued_checkpoint_sha256": self.continued_checkpoint_sha256,
            "source_order_count": self.source_order_count,
            "continued_order_count": self.continued_order_count,
            "source_fill_count": self.source_fill_count,
            "continued_fill_count": self.continued_fill_count,
            "source_event_count": self.source_event_count,
            "continued_event_count": self.continued_event_count,
            "new_order_id": self.new_order_id,
            "new_fill_id": self.new_fill_id,
        }


class RecoveryContinuationSafety:
    """Prove safe continuation after a verified checkpoint restore."""

    def __init__(
        self,
        *,
        checkpoint_manager: BrokerStateCheckpointManager | None = None,
        recovery: RestartRecoveryReplay | None = None,
        reconciler: ExecutionEventReconciler | None = None,
    ) -> None:
        self._checkpoint_manager = checkpoint_manager or BrokerStateCheckpointManager()
        self._recovery = recovery or RestartRecoveryReplay(
            checkpoint_manager=self._checkpoint_manager
        )
        self._reconciler = reconciler or ExecutionEventReconciler()

    def continue_from_checkpoint(
        self,
        checkpoint: BrokerStateCheckpoint,
        *,
        continuation_client_order_id: str = "v77-7-continuation-sell",
    ) -> tuple[OrderLifecycleSimulator, ContinuationSafetyReport]:
        simulator = self._recovery.restore(checkpoint)

        source_order_ids = {
            str(item["broker_order_id"]) for item in checkpoint.orders
        }
        source_fill_ids = {
            str(item["fill_id"]) for item in checkpoint.fills
        }
        source_sequences = [
            int(item["sequence"]) for item in checkpoint.events
        ]

        duplicate_rejected = False
        if checkpoint.orders:
            duplicate_id = str(checkpoint.orders[0]["client_order_id"])
            try:
                simulator.submit_order(
                    BrokerOrderRequest(
                        client_order_id=duplicate_id,
                        symbol="AAPL",
                        side=OrderSide.SELL,
                        quantity=Decimal("1"),
                        order_type=OrderType.MARKET,
                        time_in_force=TimeInForce.DAY,
                    )
                )
            except Exception:
                duplicate_rejected = True

        order = simulator.submit_order(
            BrokerOrderRequest(
                client_order_id=continuation_client_order_id,
                symbol="AAPL",
                side=OrderSide.SELL,
                quantity=Decimal("1"),
                order_type=OrderType.MARKET,
                time_in_force=TimeInForce.DAY,
            )
        )
        simulator.apply_fill(
            order.broker_order_id,
            quantity=Decimal("1"),
            price=Decimal("125"),
        )
        fill = simulator.list_fills()[-1]

        reconciliation = self._reconciler.reconcile(simulator)
        continued = self._checkpoint_manager.create(
            simulator,
            checkpoint_id=f"{checkpoint.checkpoint_id}-CONTINUED",
        )

        continued_order_ids = {
            str(item["broker_order_id"]) for item in continued.orders
        }
        continued_fill_ids = {
            str(item["fill_id"]) for item in continued.fills
        }
        continued_sequences = [
            int(item["sequence"]) for item in continued.events
        ]

        expected_order_sequence = max(
            [self._numeric_suffix(value) for value in source_order_ids] or [0]
        ) + 1
        expected_fill_sequence = max(
            [self._numeric_suffix(value) for value in source_fill_ids] or [0]
        ) + 1
        expected_event_start = (max(source_sequences) if source_sequences else 0) + 1

        checks = {
            "duplicate_client_order_rejected": duplicate_rejected,
            "new_order_id_unique": order.broker_order_id not in source_order_ids,
            "new_fill_id_unique": fill.fill_id not in source_fill_ids,
            "new_order_sequence_contiguous":
                self._numeric_suffix(order.broker_order_id) == expected_order_sequence,
            "new_fill_sequence_contiguous":
                self._numeric_suffix(fill.fill_id) == expected_fill_sequence,
            "new_event_sequence_contiguous":
                continued_sequences[len(source_sequences):]
                == list(range(expected_event_start, expected_event_start + 3)),
            "source_order_ids_preserved":
                source_order_ids.issubset(continued_order_ids),
            "source_fill_ids_preserved":
                source_fill_ids.issubset(continued_fill_ids),
            "reconciliation_pass": reconciliation.passed,
            "continued_checkpoint_valid":
                self._checkpoint_manager.verify(continued),
            "continued_checkpoint_changed":
                continued.state_sha256 != checkpoint.state_sha256,
            "order_count_incremented":
                len(continued.orders) == len(checkpoint.orders) + 1,
            "fill_count_incremented":
                len(continued.fills) == len(checkpoint.fills) + 1,
            "event_count_incremented":
                len(continued.events) == len(checkpoint.events) + 3,
            "actual_orders_submitted_zero":
                simulator.actual_orders_submitted == 0,
            "network_unused":
                simulator.health().network_used is False,
        }

        status = "PASS" if all(checks.values()) else "FAIL"
        report = ContinuationSafetyReport(
            status=status,
            checks=MappingProxyType(dict(checks)),
            source_checkpoint_sha256=checkpoint.state_sha256,
            continued_checkpoint_sha256=continued.state_sha256,
            source_order_count=len(checkpoint.orders),
            continued_order_count=len(continued.orders),
            source_fill_count=len(checkpoint.fills),
            continued_fill_count=len(continued.fills),
            source_event_count=len(checkpoint.events),
            continued_event_count=len(continued.events),
            new_order_id=order.broker_order_id,
            new_fill_id=fill.fill_id,
        )
        if status != "PASS":
            failed = [key for key, value in checks.items() if not value]
            raise ContinuationSafetyError(
                f"continuation safety failed: {', '.join(failed)}"
            )
        return simulator, report

    @staticmethod
    def _numeric_suffix(value: str) -> int:
        try:
            return int(value.rsplit("-", 1)[-1])
        except ValueError as exc:
            raise ContinuationSafetyError(
                f"identifier has no numeric suffix: {value}"
            ) from exc
