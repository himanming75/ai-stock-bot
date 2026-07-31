from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Iterable

from broker.contracts_v77_1 import BrokerOrderStatus, OrderSide
from broker.order_lifecycle_simulator_v77_3 import (
    OrderLifecycleSimulator,
    SandboxFill,
)


@dataclass(frozen=True)
class ReconciliationIssue:
    code: str
    message: str
    broker_order_id: str | None = None
    symbol: str | None = None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "code": self.code,
            "message": self.message,
            "broker_order_id": self.broker_order_id,
            "symbol": self.symbol,
        }


@dataclass(frozen=True)
class ReconciliationReport:
    status: str
    issue_count: int
    issues: tuple[ReconciliationIssue, ...]
    expected_cash: Decimal
    actual_cash: Decimal
    expected_positions: MappingProxyType
    actual_positions: MappingProxyType
    checked_order_count: int
    checked_fill_count: int
    checked_event_count: int

    @property
    def passed(self) -> bool:
        return self.status == "PASS"

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "issue_count": self.issue_count,
            "issues": [issue.as_dict() for issue in self.issues],
            "expected_cash": str(self.expected_cash),
            "actual_cash": str(self.actual_cash),
            "expected_positions": {
                symbol: str(quantity)
                for symbol, quantity in self.expected_positions.items()
            },
            "actual_positions": {
                symbol: str(quantity)
                for symbol, quantity in self.actual_positions.items()
            },
            "checked_order_count": self.checked_order_count,
            "checked_fill_count": self.checked_fill_count,
            "checked_event_count": self.checked_event_count,
        }


class ExecutionEventReconciler:
    """Cross-check orders, fills, account state, and lifecycle events."""

    def reconcile(self, simulator: OrderLifecycleSimulator) -> ReconciliationReport:
        orders = tuple(simulator.list_orders())
        fills = tuple(simulator.list_fills())
        events = tuple(simulator.event_ledger())
        snapshot = simulator.get_account_snapshot()
        issues: list[ReconciliationIssue] = []

        fills_by_order: dict[str, list[SandboxFill]] = {}
        for fill in fills:
            fills_by_order.setdefault(fill.broker_order_id, []).append(fill)

        for order in orders:
            order_fills = fills_by_order.get(order.broker_order_id, [])
            fill_quantity = sum((f.quantity for f in order_fills), Decimal("0"))
            fill_value = sum((f.quantity * f.price for f in order_fills), Decimal("0"))
            average = fill_value / fill_quantity if fill_quantity else None

            if fill_quantity != order.filled_quantity:
                issues.append(ReconciliationIssue(
                    "ORDER_FILL_QUANTITY_MISMATCH",
                    f"order filled quantity {order.filled_quantity} != fill ledger {fill_quantity}",
                    order.broker_order_id,
                    order.request.symbol,
                ))
            if average != order.average_fill_price:
                issues.append(ReconciliationIssue(
                    "ORDER_AVERAGE_PRICE_MISMATCH",
                    f"order average {order.average_fill_price} != fill ledger {average}",
                    order.broker_order_id,
                    order.request.symbol,
                ))

            if order.status is BrokerOrderStatus.ACCEPTED and fill_quantity != 0:
                issues.append(ReconciliationIssue(
                    "ACCEPTED_ORDER_HAS_FILLS",
                    "accepted order must not have fills",
                    order.broker_order_id,
                    order.request.symbol,
                ))
            if order.status is BrokerOrderStatus.PARTIALLY_FILLED:
                if not (Decimal("0") < fill_quantity < order.request.quantity):
                    issues.append(ReconciliationIssue(
                        "PARTIAL_STATUS_INVALID_QUANTITY",
                        "partially filled order quantity is outside valid range",
                        order.broker_order_id,
                        order.request.symbol,
                    ))
            if order.status is BrokerOrderStatus.FILLED:
                if fill_quantity != order.request.quantity:
                    issues.append(ReconciliationIssue(
                        "FILLED_STATUS_INVALID_QUANTITY",
                        "filled order quantity does not equal request",
                        order.broker_order_id,
                        order.request.symbol,
                    ))

        known_order_ids = {order.broker_order_id for order in orders}
        for fill in fills:
            if fill.broker_order_id not in known_order_ids:
                issues.append(ReconciliationIssue(
                    "ORPHAN_FILL",
                    "fill references an unknown order",
                    fill.broker_order_id,
                ))

        expected_cash = simulator._starting_cash
        expected_positions: dict[str, Decimal] = {}
        for order in orders:
            for fill in fills_by_order.get(order.broker_order_id, []):
                value = fill.quantity * fill.price
                symbol = order.request.symbol
                if order.request.side is OrderSide.BUY:
                    expected_cash -= value
                    expected_positions[symbol] = (
                        expected_positions.get(symbol, Decimal("0")) + fill.quantity
                    )
                else:
                    expected_cash += value
                    expected_positions[symbol] = (
                        expected_positions.get(symbol, Decimal("0")) - fill.quantity
                    )

        expected_positions = {
            symbol: quantity
            for symbol, quantity in expected_positions.items()
            if quantity != 0
        }
        actual_positions = {
            position.symbol: position.quantity
            for position in snapshot.positions
            if position.quantity != 0
        }

        if expected_cash != snapshot.cash:
            issues.append(ReconciliationIssue(
                "CASH_BALANCE_MISMATCH",
                f"expected cash {expected_cash} != actual cash {snapshot.cash}",
            ))
        if expected_positions != actual_positions:
            all_symbols = sorted(set(expected_positions) | set(actual_positions))
            for symbol in all_symbols:
                expected = expected_positions.get(symbol, Decimal("0"))
                actual = actual_positions.get(symbol, Decimal("0"))
                if expected != actual:
                    issues.append(ReconciliationIssue(
                        "POSITION_QUANTITY_MISMATCH",
                        f"expected position {expected} != actual position {actual}",
                        symbol=symbol,
                    ))

        fill_event_ids = {
            event.details.get("fill_id")
            for event in events
            if event.event_type in {"simulated_partial_fill", "simulated_full_fill"}
        }
        ledger_fill_ids = {fill.fill_id for fill in fills}
        if fill_event_ids != ledger_fill_ids:
            issues.append(ReconciliationIssue(
                "FILL_EVENT_LEDGER_MISMATCH",
                "fill event IDs do not match fill ledger IDs",
            ))

        event_sequences = [event.sequence for event in events]
        if event_sequences != list(range(1, len(events) + 1)):
            issues.append(ReconciliationIssue(
                "EVENT_SEQUENCE_GAP",
                "event ledger sequence is not contiguous",
            ))

        status = "PASS" if not issues else "FAIL"
        return ReconciliationReport(
            status=status,
            issue_count=len(issues),
            issues=tuple(issues),
            expected_cash=expected_cash,
            actual_cash=snapshot.cash,
            expected_positions=MappingProxyType(dict(expected_positions)),
            actual_positions=MappingProxyType(dict(actual_positions)),
            checked_order_count=len(orders),
            checked_fill_count=len(fills),
            checked_event_count=len(events),
        )
