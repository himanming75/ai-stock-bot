from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
import json
import time


class MonitorDecision(str, Enum):
    CONTINUE_TRACKING = "CONTINUE_TRACKING"
    PARTIAL_FILL_TRACKING = "PARTIAL_FILL_TRACKING"
    FILLED_COMPLETE = "FILLED_COMPLETE"
    TERMINAL_COMPLETE = "TERMINAL_COMPLETE"
    SAFE_MODE = "SAFE_MODE"


@dataclass(frozen=True)
class LifecycleSnapshot:
    sequence: int
    observed_at: str
    broker_order_id: str
    client_order_id: str
    symbol: str
    side: str
    status: str
    quantity: Decimal
    filled_quantity: Decimal
    remaining_quantity: Decimal
    average_fill_price: Decimal
    position_quantity: Decimal
    position_average_price: Decimal
    cash: Decimal
    equity: Decimal

    def to_json_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        for key in (
            "quantity",
            "filled_quantity",
            "remaining_quantity",
            "average_fill_price",
            "position_quantity",
            "position_average_price",
            "cash",
            "equity",
        ):
            raw[key] = str(raw[key])
        return raw


@dataclass(frozen=True)
class LifecycleTransition:
    sequence: int
    previous_status: str
    current_status: str
    filled_quantity_delta: Decimal
    position_quantity_delta: Decimal
    cash_delta: Decimal
    equity_delta: Decimal
    material_change: bool

    def to_json_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        for key in (
            "filled_quantity_delta",
            "position_quantity_delta",
            "cash_delta",
            "equity_delta",
        ):
            raw[key] = str(raw[key])
        return raw


@dataclass(frozen=True)
class LifecycleMonitorReport:
    decision: MonitorDecision
    terminal: bool
    safe_mode_engaged: bool
    new_order_allowed: bool
    poll_count: int
    transition_count: int
    material_transition_count: int
    final_status: str
    final_filled_quantity: str
    final_remaining_quantity: str
    final_position_quantity: str
    snapshots: tuple[LifecycleSnapshot, ...]
    transitions: tuple[LifecycleTransition, ...]
    ledger_path: str
    network_requests_executed: int
    write_requests_executed: int
    actual_paper_orders_submitted: int
    live_orders_submitted: int

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision.value,
            "terminal": self.terminal,
            "safe_mode_engaged": self.safe_mode_engaged,
            "new_order_allowed": self.new_order_allowed,
            "poll_count": self.poll_count,
            "transition_count": self.transition_count,
            "material_transition_count": self.material_transition_count,
            "final_status": self.final_status,
            "final_filled_quantity": self.final_filled_quantity,
            "final_remaining_quantity": self.final_remaining_quantity,
            "final_position_quantity": self.final_position_quantity,
            "snapshots": [item.to_json_dict() for item in self.snapshots],
            "transitions": [item.to_json_dict() for item in self.transitions],
            "ledger_path": self.ledger_path,
            "network_requests_executed": self.network_requests_executed,
            "write_requests_executed": self.write_requests_executed,
            "actual_paper_orders_submitted": self.actual_paper_orders_submitted,
            "live_orders_submitted": self.live_orders_submitted,
        }


class LifecycleLedger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, snapshot: LifecycleSnapshot) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(snapshot.to_json_dict(), sort_keys=True) + "\n")

    def read_all(self) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        records = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
        return tuple(records)


class ExistingPaperOrderLifecycleMonitor:
    ACTIVE = {
        "accepted",
        "new",
        "pending_new",
        "pending_replace",
        "held",
        "calculated",
    }
    PARTIAL = {"partially_filled"}
    FILLED = {"filled"}
    TERMINAL = {
        "canceled",
        "cancelled",
        "rejected",
        "expired",
        "done_for_day",
        "replaced",
    }

    def __init__(self, *, ledger: LifecycleLedger) -> None:
        self.ledger = ledger

    def monitor(
        self,
        *,
        poller: Callable[[int], LifecycleSnapshot],
        max_polls: int,
        poll_interval_seconds: float = 0.0,
        stop_on_material_transition: bool = False,
        network_requests_per_poll: int = 3,
    ) -> LifecycleMonitorReport:
        if max_polls <= 0:
            raise ValueError("max_polls must be positive")
        if poll_interval_seconds < 0:
            raise ValueError("poll_interval_seconds cannot be negative")
        if network_requests_per_poll < 0:
            raise ValueError("network_requests_per_poll cannot be negative")

        snapshots: list[LifecycleSnapshot] = []
        transitions: list[LifecycleTransition] = []

        for sequence in range(1, max_polls + 1):
            snapshot = poller(sequence)
            if snapshot.sequence != sequence:
                raise ValueError("snapshot sequence mismatch")
            self.ledger.append(snapshot)
            snapshots.append(snapshot)

            if len(snapshots) > 1:
                transition = self._transition(snapshots[-2], snapshots[-1])
                transitions.append(transition)
                if stop_on_material_transition and transition.material_change:
                    break

            status = snapshot.status.lower()
            if status in self.FILLED or status in self.TERMINAL:
                break

            if sequence < max_polls and poll_interval_seconds:
                time.sleep(poll_interval_seconds)

        final = snapshots[-1]
        decision, terminal, safe_mode, allowed = self._decision(final)

        return LifecycleMonitorReport(
            decision=decision,
            terminal=terminal,
            safe_mode_engaged=safe_mode,
            new_order_allowed=allowed,
            poll_count=len(snapshots),
            transition_count=len(transitions),
            material_transition_count=sum(
                1 for item in transitions if item.material_change
            ),
            final_status=final.status,
            final_filled_quantity=str(final.filled_quantity),
            final_remaining_quantity=str(final.remaining_quantity),
            final_position_quantity=str(final.position_quantity),
            snapshots=tuple(snapshots),
            transitions=tuple(transitions),
            ledger_path=str(self.ledger.path),
            network_requests_executed=(
                len(snapshots) * network_requests_per_poll
            ),
            write_requests_executed=0,
            actual_paper_orders_submitted=0,
            live_orders_submitted=0,
        )

    @classmethod
    def _decision(
        cls,
        snapshot: LifecycleSnapshot,
    ) -> tuple[MonitorDecision, bool, bool, bool]:
        status = snapshot.status.lower()

        if status in cls.ACTIVE:
            return (
                MonitorDecision.CONTINUE_TRACKING,
                False,
                False,
                False,
            )
        if status in cls.PARTIAL:
            valid = (
                snapshot.filled_quantity > 0
                and snapshot.remaining_quantity > 0
                and snapshot.filled_quantity < snapshot.quantity
            )
            if not valid:
                return MonitorDecision.SAFE_MODE, False, True, False
            return (
                MonitorDecision.PARTIAL_FILL_TRACKING,
                False,
                False,
                False,
            )
        if status in cls.FILLED:
            valid = (
                snapshot.quantity > 0
                and snapshot.filled_quantity == snapshot.quantity
                and snapshot.remaining_quantity == 0
            )
            if not valid:
                return MonitorDecision.SAFE_MODE, True, True, False
            return (
                MonitorDecision.FILLED_COMPLETE,
                True,
                False,
                True,
            )
        if status in cls.TERMINAL:
            return (
                MonitorDecision.TERMINAL_COMPLETE,
                True,
                False,
                True,
            )
        return MonitorDecision.SAFE_MODE, False, True, False

    @staticmethod
    def _transition(
        previous: LifecycleSnapshot,
        current: LifecycleSnapshot,
    ) -> LifecycleTransition:
        status_changed = previous.status.lower() != current.status.lower()
        fill_delta = current.filled_quantity - previous.filled_quantity
        position_delta = (
            current.position_quantity - previous.position_quantity
        )
        cash_delta = current.cash - previous.cash
        equity_delta = current.equity - previous.equity
        material = (
            status_changed
            or fill_delta != 0
            or position_delta != 0
            or cash_delta != 0
            or equity_delta != 0
        )
        return LifecycleTransition(
            sequence=current.sequence,
            previous_status=previous.status,
            current_status=current.status,
            filled_quantity_delta=fill_delta,
            position_quantity_delta=position_delta,
            cash_delta=cash_delta,
            equity_delta=equity_delta,
            material_change=material,
        )


def build_snapshot(
    *,
    sequence: int,
    observed_at: str,
    order: Mapping[str, Any],
    positions: Sequence[Mapping[str, Any]],
    account: Mapping[str, Any],
) -> LifecycleSnapshot:
    symbol = _text(order.get("symbol")).upper()
    quantity = _decimal(order.get("quantity", order.get("qty", "0")))
    filled = _decimal(
        order.get("filled_quantity", order.get("filled_qty", "0"))
    )
    remaining = max(Decimal("0"), quantity - filled)
    position = next(
        (
            item
            for item in positions
            if _text(item.get("symbol")).upper() == symbol
        ),
        None,
    )

    return LifecycleSnapshot(
        sequence=sequence,
        observed_at=observed_at,
        broker_order_id=_text(
            order.get("broker_order_id", order.get("id"))
        ),
        client_order_id=_text(order.get("client_order_id")),
        symbol=symbol,
        side=_text(order.get("side")).upper(),
        status=_text(order.get("status")).upper(),
        quantity=quantity,
        filled_quantity=filled,
        remaining_quantity=remaining,
        average_fill_price=_decimal(
            order.get(
                "average_fill_price",
                order.get("filled_avg_price", "0"),
            )
        ),
        position_quantity=_decimal(
            position.get("quantity", position.get("qty", "0"))
            if position
            else "0"
        ),
        position_average_price=_decimal(
            position.get(
                "average_entry_price",
                position.get("average_price", "0"),
            )
            if position
            else "0"
        ),
        cash=_decimal(account.get("cash", "0")),
        equity=_decimal(account.get("equity", "0")),
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
