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
from broker.restart_recovery_replay_v77_6 import RestartRecoveryReplay


class MultiOrderStressError(ValueError):
    """Raised when multi-order continuation stress verification fails."""


@dataclass(frozen=True)
class MultiOrderStressReport:
    status: str
    checks: MappingProxyType
    source_state_sha256: str
    stressed_state_sha256: str
    submitted_order_count: int
    applied_fill_count: int
    duplicate_rejection_count: int
    symbols: tuple[str, ...]
    new_order_ids: tuple[str, ...]
    new_fill_ids: tuple[str, ...]
    final_positions: tuple[MappingProxyType, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "checks": dict(self.checks),
            "source_state_sha256": self.source_state_sha256,
            "stressed_state_sha256": self.stressed_state_sha256,
            "submitted_order_count": self.submitted_order_count,
            "applied_fill_count": self.applied_fill_count,
            "duplicate_rejection_count": self.duplicate_rejection_count,
            "symbols": list(self.symbols),
            "new_order_ids": list(self.new_order_ids),
            "new_fill_ids": list(self.new_fill_ids),
            "final_positions": [dict(item) for item in self.final_positions],
        }


class MultiOrderContinuationStress:
    """Run deterministic offline multi-symbol continuation stress."""

    def __init__(
        self,
        *,
        checkpoint_manager: BrokerStateCheckpointManager | None = None,
        recovery: RestartRecoveryReplay | None = None,
        reconciler: ExecutionEventReconciler | None = None,
    ) -> None:
        self._manager = checkpoint_manager or BrokerStateCheckpointManager()
        self._recovery = recovery or RestartRecoveryReplay(
            checkpoint_manager=self._manager
        )
        self._reconciler = reconciler or ExecutionEventReconciler()

    def run(
        self,
        checkpoint: BrokerStateCheckpoint,
    ) -> tuple[object, MultiOrderStressReport]:
        simulator = self._recovery.restore(checkpoint)
        source_order_ids = [str(x["broker_order_id"]) for x in checkpoint.orders]
        source_fill_ids = [str(x["fill_id"]) for x in checkpoint.fills]
        source_event_sequences = [int(x["sequence"]) for x in checkpoint.events]

        plans = (
            ("stress-msft-buy-1", "MSFT", OrderSide.BUY, "8", (("3", "300"), ("5", "304"))),
            ("stress-nvda-buy-1", "NVDA", OrderSide.BUY, "12", (("12", "120"),)),
            ("stress-aapl-buy-1", "AAPL", OrderSide.BUY, "4", (("2", "126"), ("2", "128"))),
            ("stress-msft-sell-1", "MSFT", OrderSide.SELL, "2", (("2", "310"),)),
            ("stress-nvda-sell-1", "NVDA", OrderSide.SELL, "5", (("2", "125"), ("3", "127"))),
            ("stress-aapl-sell-1", "AAPL", OrderSide.SELL, "3", (("3", "130"),)),
            ("stress-msft-buy-2", "MSFT", OrderSide.BUY, "1", (("1", "306"),)),
            ("stress-nvda-buy-2", "NVDA", OrderSide.BUY, "2", (("1", "121"), ("1", "122"))),
        )

        duplicate_rejections = 0
        for duplicate_id in (
            str(checkpoint.orders[0]["client_order_id"]),
            str(checkpoint.orders[-1]["client_order_id"]),
        ):
            try:
                simulator.submit_order(BrokerOrderRequest(
                    client_order_id=duplicate_id,
                    symbol="AAPL",
                    side=OrderSide.BUY,
                    quantity=Decimal("1"),
                    order_type=OrderType.MARKET,
                    time_in_force=TimeInForce.DAY,
                ))
            except Exception:
                duplicate_rejections += 1

        new_order_ids: list[str] = []
        fill_count_before = len(simulator.list_fills())
        for client_id, symbol, side, quantity, fills in plans:
            order = simulator.submit_order(BrokerOrderRequest(
                client_order_id=client_id,
                symbol=symbol,
                side=side,
                quantity=Decimal(quantity),
                order_type=OrderType.MARKET,
                time_in_force=TimeInForce.DAY,
            ))
            new_order_ids.append(order.broker_order_id)
            for fill_quantity, fill_price in fills:
                simulator.apply_fill(
                    order.broker_order_id,
                    quantity=Decimal(fill_quantity),
                    price=Decimal(fill_price),
                )

        all_fills = simulator.list_fills()
        new_fills = all_fills[fill_count_before:]
        new_fill_ids = [fill.fill_id for fill in new_fills]
        reconciliation = self._reconciler.reconcile(simulator)
        stressed = self._manager.create(
            simulator,
            checkpoint_id=f"{checkpoint.checkpoint_id}-STRESS",
        )

        new_sequences = [
            int(item["sequence"]) for item in stressed.events
        ][len(source_event_sequences):]
        expected_event_count = (
            duplicate_rejections
            + len(plans)
            + sum(len(plan[4]) for plan in plans)
        )
        first_order_sequence = max(
            [self._suffix(value) for value in source_order_ids] or [0]
        ) + 1
        first_fill_sequence = max(
            [self._suffix(value) for value in source_fill_ids] or [0]
        ) + 1
        first_event_sequence = max(source_event_sequences or [0]) + 1

        positions = {
            str(item["symbol"]): Decimal(str(item["quantity"]))
            for item in stressed.positions
        }
        source_positions = {
            str(item["symbol"]): Decimal(str(item["quantity"]))
            for item in checkpoint.positions
        }
        checks = {
            "duplicate_rejections_complete": duplicate_rejections == 2,
            "order_count_exact": len(new_order_ids) == 8,
            "fill_count_exact": len(new_fill_ids) == 12,
            "order_ids_unique": len(set(new_order_ids)) == len(new_order_ids),
            "fill_ids_unique": len(set(new_fill_ids)) == len(new_fill_ids),
            "order_ids_contiguous": [
                self._suffix(value) for value in new_order_ids
            ] == list(range(first_order_sequence, first_order_sequence + 8)),
            "fill_ids_contiguous": [
                self._suffix(value) for value in new_fill_ids
            ] == list(range(first_fill_sequence, first_fill_sequence + 12)),
            "event_sequences_contiguous": new_sequences == list(
                range(first_event_sequence, first_event_sequence + expected_event_count)
            ),
            "event_count_exact": len(new_sequences) == expected_event_count,
            "all_symbols_present": set(positions) == {"AAPL", "MSFT", "NVDA"},
            "aapl_quantity_expected":
                positions.get("AAPL")
                == source_positions.get("AAPL", Decimal("0")) + Decimal("1"),
            "msft_quantity_expected": positions.get("MSFT") == Decimal("7"),
            "nvda_quantity_expected": positions.get("NVDA") == Decimal("9"),
            "reconciliation_pass": reconciliation.passed,
            "checkpoint_valid": self._manager.verify(stressed),
            "checkpoint_changed": stressed.state_sha256 != checkpoint.state_sha256,
            "network_unused": simulator.health().network_used is False,
            "broker_disconnected": simulator.health().connected is False,
            "actual_orders_zero": simulator.actual_orders_submitted == 0,
        }
        status = "PASS" if all(checks.values()) else "FAIL"
        report = MultiOrderStressReport(
            status=status,
            checks=MappingProxyType(checks),
            source_state_sha256=checkpoint.state_sha256,
            stressed_state_sha256=stressed.state_sha256,
            submitted_order_count=len(new_order_ids),
            applied_fill_count=len(new_fill_ids),
            duplicate_rejection_count=duplicate_rejections,
            symbols=tuple(sorted(positions)),
            new_order_ids=tuple(new_order_ids),
            new_fill_ids=tuple(new_fill_ids),
            final_positions=stressed.positions,
        )
        if status != "PASS":
            failed = [key for key, value in checks.items() if not value]
            raise MultiOrderStressError(
                f"multi-order stress failed: {', '.join(failed)}"
            )
        return simulator, report

    @staticmethod
    def _suffix(value: str) -> int:
        try:
            return int(value.rsplit("-", 1)[-1])
        except ValueError as exc:
            raise MultiOrderStressError(
                f"identifier has no numeric suffix: {value}"
            ) from exc
