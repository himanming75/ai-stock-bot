from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence
import json


class CompletionGateState(str, Enum):
    LOCKED_ACTIVE_ORDER = "LOCKED_ACTIVE_ORDER"
    LOCKED_PARTIAL_FILL = "LOCKED_PARTIAL_FILL"
    UNLOCKED_FILLED = "UNLOCKED_FILLED"
    UNLOCKED_TERMINAL_NO_FILL = "UNLOCKED_TERMINAL_NO_FILL"
    SAFE_MODE = "SAFE_MODE"


@dataclass(frozen=True)
class CompletionGateIssue:
    code: str
    expected: str
    actual: str
    blocking: bool
    detail: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CompletionLedgerEntry:
    event_type: str
    client_order_id: str
    broker_order_id: str
    symbol: str
    side: str
    final_status: str
    quantity: str
    filled_quantity: str
    remaining_quantity: str
    average_fill_price: str
    position_quantity: str
    cash: str
    equity: str
    completed_at: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CompletionUnlockReport:
    state: CompletionGateState
    completion_verified: bool
    new_order_allowed: bool
    safe_mode_engaged: bool
    terminal: bool
    final_status: str
    filled_quantity: str
    remaining_quantity: str
    position_quantity: str
    issue_count: int
    blocking_issue_count: int
    issues: tuple[CompletionGateIssue, ...]
    ledger_entry_written: bool
    ledger_path: str
    network_requests_executed: int
    write_requests_executed: int
    actual_paper_orders_submitted: int
    live_orders_submitted: int

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "completion_verified": self.completion_verified,
            "new_order_allowed": self.new_order_allowed,
            "safe_mode_engaged": self.safe_mode_engaged,
            "terminal": self.terminal,
            "final_status": self.final_status,
            "filled_quantity": self.filled_quantity,
            "remaining_quantity": self.remaining_quantity,
            "position_quantity": self.position_quantity,
            "issue_count": self.issue_count,
            "blocking_issue_count": self.blocking_issue_count,
            "issues": [item.to_json_dict() for item in self.issues],
            "ledger_entry_written": self.ledger_entry_written,
            "ledger_path": self.ledger_path,
            "network_requests_executed": self.network_requests_executed,
            "write_requests_executed": self.write_requests_executed,
            "actual_paper_orders_submitted": self.actual_paper_orders_submitted,
            "live_orders_submitted": self.live_orders_submitted,
        }


class CompletionLedger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, entry: CompletionLedgerEntry) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.to_json_dict(), sort_keys=True) + "\n")

    def read_all(self) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        rows = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return tuple(rows)


class OrderCompletionNextOrderUnlockGate:
    ACTIVE = {"accepted", "new", "pending_new", "pending_replace", "held", "calculated"}
    PARTIAL = {"partially_filled"}
    FILLED = {"filled"}
    TERMINAL_NO_FILL = {"canceled", "cancelled", "rejected", "expired", "done_for_day", "replaced"}

    def __init__(self, *, ledger: CompletionLedger) -> None:
        self.ledger = ledger

    def evaluate(
        self,
        *,
        lifecycle_result: Mapping[str, Any],
        completed_at: str,
        network_requests_executed: int = 0,
    ) -> CompletionUnlockReport:
        status = _text(
            lifecycle_result.get(
                "final_status",
                lifecycle_result.get("broker_status", ""),
            )
        ).lower()
        quantity = _decimal(
            lifecycle_result.get("quantity", "0")
        )
        filled = _decimal(
            lifecycle_result.get(
                "final_filled_quantity",
                lifecycle_result.get("filled_quantity", "0"),
            )
        )
        remaining = _decimal(
            lifecycle_result.get(
                "final_remaining_quantity",
                lifecycle_result.get("remaining_quantity", "0"),
            )
        )
        position = _decimal(
            lifecycle_result.get(
                "final_position_quantity",
                lifecycle_result.get("position_quantity", "0"),
            )
        )
        issues: list[CompletionGateIssue] = []
        ledger_written = False

        if status in self.ACTIVE:
            state = CompletionGateState.LOCKED_ACTIVE_ORDER
            terminal = False
            verified = False
            allowed = False

        elif status in self.PARTIAL:
            state = CompletionGateState.LOCKED_PARTIAL_FILL
            terminal = False
            verified = False
            allowed = False
            if not (Decimal("0") < filled < quantity and remaining > 0):
                issues.append(CompletionGateIssue(
                    code="INVALID_PARTIAL_STATE",
                    expected="0 < filled < quantity and remaining > 0",
                    actual=f"filled={filled}, quantity={quantity}, remaining={remaining}",
                    blocking=True,
                    detail="partial-fill state is internally inconsistent",
                ))

        elif status in self.FILLED:
            state = CompletionGateState.UNLOCKED_FILLED
            terminal = True
            verified = True
            allowed = True
            if quantity <= 0:
                issues.append(CompletionGateIssue(
                    code="INVALID_FILLED_QUANTITY",
                    expected="quantity > 0",
                    actual=str(quantity),
                    blocking=True,
                    detail="filled order has invalid requested quantity",
                ))
            if filled != quantity:
                issues.append(CompletionGateIssue(
                    code="FILLED_QUANTITY_MISMATCH",
                    expected=str(quantity),
                    actual=str(filled),
                    blocking=True,
                    detail="filled quantity must equal requested quantity",
                ))
            if remaining != 0:
                issues.append(CompletionGateIssue(
                    code="FILLED_REMAINDER_NONZERO",
                    expected="0",
                    actual=str(remaining),
                    blocking=True,
                    detail="filled order must have zero remaining quantity",
                ))
            side = _text(lifecycle_result.get("side", "")).upper()
            if side == "BUY" and position < filled:
                issues.append(CompletionGateIssue(
                    code="POSITION_NOT_UPDATED",
                    expected=f">={filled}",
                    actual=str(position),
                    blocking=True,
                    detail="BUY fill is not reflected in broker position",
                ))

        elif status in self.TERMINAL_NO_FILL:
            state = CompletionGateState.UNLOCKED_TERMINAL_NO_FILL
            terminal = True
            verified = True
            allowed = True
            if filled > 0 and position < filled:
                issues.append(CompletionGateIssue(
                    code="PARTIAL_TERMINAL_POSITION_MISMATCH",
                    expected=f">={filled}",
                    actual=str(position),
                    blocking=True,
                    detail="partial fill from terminal order is not reflected in position",
                ))

        else:
            state = CompletionGateState.SAFE_MODE
            terminal = False
            verified = False
            allowed = False
            issues.append(CompletionGateIssue(
                code="UNKNOWN_FINAL_STATUS",
                expected="known active, partial, filled, or terminal status",
                actual=status,
                blocking=True,
                detail="unknown order status requires operator review",
            ))

        blocking = sum(1 for item in issues if item.blocking)
        safe_mode = blocking > 0 or state == CompletionGateState.SAFE_MODE
        if safe_mode:
            verified = False
            allowed = False

        if verified and terminal:
            entry = CompletionLedgerEntry(
                event_type="ORDER_COMPLETED",
                client_order_id=_text(lifecycle_result.get("client_order_id", "")),
                broker_order_id=_text(lifecycle_result.get("broker_order_id", "")),
                symbol=_text(lifecycle_result.get("symbol", "")).upper(),
                side=_text(lifecycle_result.get("side", "")).upper(),
                final_status=status.upper(),
                quantity=str(quantity),
                filled_quantity=str(filled),
                remaining_quantity=str(remaining),
                average_fill_price=_text(
                    lifecycle_result.get("average_fill_price", "0")
                ),
                position_quantity=str(position),
                cash=_text(lifecycle_result.get("cash", "0")),
                equity=_text(lifecycle_result.get("equity", "0")),
                completed_at=completed_at,
            )
            self.ledger.append(entry)
            ledger_written = True

        return CompletionUnlockReport(
            state=state,
            completion_verified=verified,
            new_order_allowed=allowed,
            safe_mode_engaged=safe_mode,
            terminal=terminal,
            final_status=status.upper(),
            filled_quantity=str(filled),
            remaining_quantity=str(remaining),
            position_quantity=str(position),
            issue_count=len(issues),
            blocking_issue_count=blocking,
            issues=tuple(issues),
            ledger_entry_written=ledger_written,
            ledger_path=str(self.ledger.path),
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
