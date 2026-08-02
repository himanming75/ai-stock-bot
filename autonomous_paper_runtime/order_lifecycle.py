from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import Enum
from typing import Any


class LifecycleClass(str, Enum):
    ACTIVE = "ACTIVE"
    PARTIAL = "PARTIAL"
    TERMINAL_SUCCESS = "TERMINAL_SUCCESS"
    TERMINAL_NO_FILL = "TERMINAL_NO_FILL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class PaperOrderLifecycleReport:
    client_order_id: str
    broker_order_id: str
    symbol: str
    side: str
    quantity: str
    filled_quantity: str
    remaining_quantity: str
    fill_ratio: str
    broker_status: str
    lifecycle_class: LifecycleClass
    terminal: bool
    new_order_allowed: bool
    safe_mode_engaged: bool
    reason: str
    network_requests_executed: int
    write_requests_executed: int
    actual_paper_orders_submitted: int
    live_orders_submitted: int

    def to_json_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["lifecycle_class"] = self.lifecycle_class.value
        return raw


class ExistingPaperOrderLifecycleTracker:
    ACTIVE = {"accepted", "new", "pending_new", "pending_replace", "held", "calculated"}
    PARTIAL = {"partially_filled"}
    SUCCESS = {"filled"}
    NO_FILL = {"canceled", "cancelled", "rejected", "expired", "done_for_day", "replaced"}

    def track(self, order: Any, *, network_requests_executed: int = 0) -> PaperOrderLifecycleReport:
        status = str(getattr(order, "status", "")).lower().strip()
        qty = Decimal(str(getattr(order, "quantity", "0")))
        filled = Decimal(str(getattr(order, "filled_quantity", "0")))
        remaining = max(Decimal("0"), qty - filled)
        ratio = Decimal("0") if qty <= 0 else filled / qty

        if status in self.ACTIVE:
            lifecycle = LifecycleClass.ACTIVE
            terminal = False
            reason = "order_active_new_orders_blocked"
        elif status in self.PARTIAL:
            lifecycle = LifecycleClass.PARTIAL
            terminal = False
            reason = "order_partially_filled_new_orders_blocked"
        elif status in self.SUCCESS:
            lifecycle = LifecycleClass.TERMINAL_SUCCESS
            terminal = True
            reason = "order_filled_ready_for_fill_reconciliation"
        elif status in self.NO_FILL:
            lifecycle = LifecycleClass.TERMINAL_NO_FILL
            terminal = True
            reason = "order_terminal_without_active_remainder"
        else:
            lifecycle = LifecycleClass.UNKNOWN
            terminal = False
            reason = "unknown_order_status_safe_mode"

        unknown = lifecycle == LifecycleClass.UNKNOWN
        return PaperOrderLifecycleReport(
            client_order_id=str(getattr(order, "client_order_id", "")),
            broker_order_id=str(getattr(order, "order_id", getattr(order, "id", ""))),
            symbol=str(getattr(order, "symbol", "")).upper(),
            side=str(getattr(order, "side", "")).upper(),
            quantity=str(qty),
            filled_quantity=str(filled),
            remaining_quantity=str(remaining),
            fill_ratio=str(ratio),
            broker_status=status.upper(),
            lifecycle_class=lifecycle,
            terminal=terminal,
            new_order_allowed=terminal and not unknown,
            safe_mode_engaged=unknown,
            reason=reason,
            network_requests_executed=network_requests_executed,
            write_requests_executed=0,
            actual_paper_orders_submitted=0,
            live_orders_submitted=0,
        )
