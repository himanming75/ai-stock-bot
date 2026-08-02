from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping, Sequence


class FillReconciliationState(str, Enum):
    WAITING_ACTIVE_ORDER = "WAITING_ACTIVE_ORDER"
    WAITING_PARTIAL_FILL = "WAITING_PARTIAL_FILL"
    FILLED_RECONCILED = "FILLED_RECONCILED"
    TERMINAL_NO_FILL = "TERMINAL_NO_FILL"
    SAFE_MODE = "SAFE_MODE"


@dataclass(frozen=True)
class FillReconciliationIssue:
    code: str
    expected: str
    actual: str
    blocking: bool
    detail: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FillReconciliationReport:
    state: FillReconciliationState
    terminal: bool
    safe_mode_engaged: bool
    new_order_allowed: bool
    client_order_id: str
    broker_order_id: str
    symbol: str
    side: str
    quantity: str
    filled_quantity: str
    remaining_quantity: str
    average_fill_price: str
    broker_status: str
    position_quantity: str
    position_average_price: str
    cash: str
    equity: str
    issue_count: int
    blocking_issue_count: int
    issues: tuple[FillReconciliationIssue, ...]
    network_requests_executed: int
    write_requests_executed: int
    actual_paper_orders_submitted: int
    live_orders_submitted: int

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "terminal": self.terminal,
            "safe_mode_engaged": self.safe_mode_engaged,
            "new_order_allowed": self.new_order_allowed,
            "client_order_id": self.client_order_id,
            "broker_order_id": self.broker_order_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "filled_quantity": self.filled_quantity,
            "remaining_quantity": self.remaining_quantity,
            "average_fill_price": self.average_fill_price,
            "broker_status": self.broker_status,
            "position_quantity": self.position_quantity,
            "position_average_price": self.position_average_price,
            "cash": self.cash,
            "equity": self.equity,
            "issue_count": self.issue_count,
            "blocking_issue_count": self.blocking_issue_count,
            "issues": [item.to_json_dict() for item in self.issues],
            "network_requests_executed": self.network_requests_executed,
            "write_requests_executed": self.write_requests_executed,
            "actual_paper_orders_submitted": self.actual_paper_orders_submitted,
            "live_orders_submitted": self.live_orders_submitted,
        }


@dataclass(frozen=True)
class FillReconciliationPolicy:
    quantity_tolerance: Decimal = Decimal("0")
    average_price_tolerance: Decimal = Decimal("0.01")

    def validate(self) -> None:
        if self.quantity_tolerance < 0:
            raise ValueError("quantity_tolerance cannot be negative")
        if self.average_price_tolerance < 0:
            raise ValueError("average_price_tolerance cannot be negative")


class ActualOrderLifecycleFillReconciler:
    ACTIVE = {"accepted", "new", "pending_new", "pending_replace", "held", "calculated"}
    PARTIAL = {"partially_filled"}
    FILLED = {"filled"}
    TERMINAL_NO_FILL = {"canceled", "cancelled", "rejected", "expired", "done_for_day", "replaced"}

    def __init__(self, *, policy: FillReconciliationPolicy | None = None) -> None:
        self.policy = policy or FillReconciliationPolicy()
        self.policy.validate()

    def reconcile(
        self,
        *,
        order: Mapping[str, Any],
        positions: Sequence[Mapping[str, Any]],
        account: Mapping[str, Any],
        network_requests_executed: int = 0,
    ) -> FillReconciliationReport:
        status = _text(order.get("status")).lower()
        symbol = _text(order.get("symbol")).upper()
        side = _text(order.get("side")).upper()
        quantity = _decimal(order.get("quantity", order.get("qty", "0")))
        filled_quantity = _decimal(
            order.get("filled_quantity", order.get("filled_qty", "0"))
        )
        remaining = max(Decimal("0"), quantity - filled_quantity)
        average_fill_price = _decimal(
            order.get("average_fill_price", order.get("filled_avg_price", "0"))
        )

        position = next(
            (
                item for item in positions
                if _text(item.get("symbol")).upper() == symbol
            ),
            None,
        )
        position_quantity = _decimal(
            position.get("quantity", position.get("qty", "0"))
            if position else "0"
        )
        position_average_price = _decimal(
            position.get(
                "average_entry_price",
                position.get("average_price", "0"),
            )
            if position else "0"
        )

        issues: list[FillReconciliationIssue] = []

        if status in self.ACTIVE:
            state = FillReconciliationState.WAITING_ACTIVE_ORDER
            terminal = False
            new_order_allowed = False
        elif status in self.PARTIAL:
            state = FillReconciliationState.WAITING_PARTIAL_FILL
            terminal = False
            new_order_allowed = False
            if filled_quantity <= 0 or remaining <= 0:
                issues.append(FillReconciliationIssue(
                    code="INVALID_PARTIAL_FILL_QUANTITY",
                    expected="0 < filled_quantity < quantity",
                    actual=f"{filled_quantity}/{quantity}",
                    blocking=True,
                    detail="partially filled order has inconsistent quantities",
                ))
        elif status in self.FILLED:
            state = FillReconciliationState.FILLED_RECONCILED
            terminal = True
            new_order_allowed = True
            if abs(filled_quantity - quantity) > self.policy.quantity_tolerance:
                issues.append(FillReconciliationIssue(
                    code="FILLED_QUANTITY_MISMATCH",
                    expected=str(quantity),
                    actual=str(filled_quantity),
                    blocking=True,
                    detail="filled order quantity differs from requested quantity",
                ))
            expected_position = filled_quantity if side == "BUY" else Decimal("0")
            if side == "BUY" and abs(position_quantity - expected_position) > self.policy.quantity_tolerance:
                issues.append(FillReconciliationIssue(
                    code="POSITION_QUANTITY_MISMATCH",
                    expected=str(expected_position),
                    actual=str(position_quantity),
                    blocking=True,
                    detail="broker position quantity does not reflect filled BUY",
                ))
            if side == "BUY" and average_fill_price > 0:
                if abs(position_average_price - average_fill_price) > self.policy.average_price_tolerance:
                    issues.append(FillReconciliationIssue(
                        code="AVERAGE_PRICE_MISMATCH",
                        expected=str(average_fill_price),
                        actual=str(position_average_price),
                        blocking=True,
                        detail="position average price differs from order average fill price",
                    ))
        elif status in self.TERMINAL_NO_FILL:
            state = FillReconciliationState.TERMINAL_NO_FILL
            terminal = True
            new_order_allowed = True
            if remaining > 0 and filled_quantity > 0:
                # Partial fill followed by cancel/expire: portfolio must retain filled quantity.
                if abs(position_quantity - filled_quantity) > self.policy.quantity_tolerance:
                    issues.append(FillReconciliationIssue(
                        code="TERMINAL_PARTIAL_POSITION_MISMATCH",
                        expected=str(filled_quantity),
                        actual=str(position_quantity),
                        blocking=True,
                        detail="terminal partially filled order does not match broker position",
                    ))
        else:
            state = FillReconciliationState.SAFE_MODE
            terminal = False
            new_order_allowed = False
            issues.append(FillReconciliationIssue(
                code="UNKNOWN_ORDER_STATUS",
                expected="known Alpaca order status",
                actual=status,
                blocking=True,
                detail="unknown broker order status requires operator review",
            ))

        blocking = sum(1 for item in issues if item.blocking)
        safe_mode = blocking > 0 or state == FillReconciliationState.SAFE_MODE
        if safe_mode:
            new_order_allowed = False

        return FillReconciliationReport(
            state=state,
            terminal=terminal,
            safe_mode_engaged=safe_mode,
            new_order_allowed=new_order_allowed,
            client_order_id=_text(order.get("client_order_id")),
            broker_order_id=_text(order.get("broker_order_id", order.get("id"))),
            symbol=symbol,
            side=side,
            quantity=str(quantity),
            filled_quantity=str(filled_quantity),
            remaining_quantity=str(remaining),
            average_fill_price=str(average_fill_price),
            broker_status=status.upper(),
            position_quantity=str(position_quantity),
            position_average_price=str(position_average_price),
            cash=str(_decimal(account.get("cash", "0"))),
            equity=str(_decimal(account.get("equity", "0"))),
            issue_count=len(issues),
            blocking_issue_count=blocking,
            issues=tuple(issues),
            network_requests_executed=network_requests_executed,
            write_requests_executed=0,
            actual_paper_orders_submitted=0,
            live_orders_submitted=0,
        )


def _text(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        value = value.value
    return str(value).strip()


def _decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    return Decimal(str(value))
