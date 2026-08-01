from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping, Sequence


class ReconciliationStatus(str, Enum):
    MATCHED = "MATCHED"
    MISMATCH = "MISMATCH"
    SAFE_MODE = "SAFE_MODE"


@dataclass(frozen=True)
class ReconciliationIssue:
    code: str
    expected: str
    actual: str
    blocking: bool
    detail: str


@dataclass(frozen=True)
class AutonomousReconciliationReport:
    status: ReconciliationStatus
    safe_mode_engaged: bool
    autonomous_order_allowed: bool
    issue_count: int
    blocking_issue_count: int
    cash_matched: bool
    equity_matched: bool
    position_count_matched: bool
    position_symbols_matched: bool
    open_order_count_matched: bool
    recovery_generation_matched: bool
    runtime_state_matched: bool
    issues: tuple[ReconciliationIssue, ...]
    network_requests_executed: int
    write_requests_executed: int
    actual_paper_orders_submitted: int
    live_orders_submitted: int

    def to_json_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["status"] = self.status.value
        raw["issues"] = [asdict(item) for item in self.issues]
        return raw


@dataclass(frozen=True)
class ReconciliationPolicy:
    cash_tolerance: Decimal = Decimal("0.01")
    equity_tolerance: Decimal = Decimal("0.01")
    block_on_open_order_mismatch: bool = True
    block_on_position_mismatch: bool = True
    block_on_recovery_mismatch: bool = True
    block_on_runtime_state_mismatch: bool = True

    def validate(self) -> None:
        if self.cash_tolerance < 0:
            raise ValueError("cash_tolerance cannot be negative")
        if self.equity_tolerance < 0:
            raise ValueError("equity_tolerance cannot be negative")


class AutonomousPaperReadReconciler:
    """Compares actual Paper read data with internal runtime state."""

    def __init__(self, *, policy: ReconciliationPolicy | None = None) -> None:
        self.policy = policy or ReconciliationPolicy()
        self.policy.validate()

    def reconcile(
        self,
        *,
        actual_snapshot: Mapping[str, Any],
        internal_portfolio: Mapping[str, Any],
        internal_recovery: Mapping[str, Any],
        internal_runtime: Mapping[str, Any],
    ) -> AutonomousReconciliationReport:
        issues: list[ReconciliationIssue] = []

        actual_cash = _decimal(actual_snapshot.get("cash", "0"))
        internal_cash = _decimal(internal_portfolio.get("cash", "0"))
        cash_matched = abs(actual_cash - internal_cash) <= self.policy.cash_tolerance
        if not cash_matched:
            issues.append(ReconciliationIssue(
                code="CASH_MISMATCH",
                expected=str(internal_cash),
                actual=str(actual_cash),
                blocking=True,
                detail="actual Alpaca Paper cash differs from internal portfolio cash",
            ))

        actual_equity = _decimal(actual_snapshot.get("equity", "0"))
        internal_equity = _decimal(internal_portfolio.get("equity", "0"))
        equity_matched = (
            abs(actual_equity - internal_equity) <= self.policy.equity_tolerance
        )
        if not equity_matched:
            issues.append(ReconciliationIssue(
                code="EQUITY_MISMATCH",
                expected=str(internal_equity),
                actual=str(actual_equity),
                blocking=True,
                detail="actual Alpaca Paper equity differs from internal portfolio equity",
            ))

        actual_position_count = int(actual_snapshot.get("position_count", 0))
        internal_positions = tuple(internal_portfolio.get("positions", ()))
        internal_position_count = len(internal_positions)
        position_count_matched = actual_position_count == internal_position_count
        if not position_count_matched:
            issues.append(ReconciliationIssue(
                code="POSITION_COUNT_MISMATCH",
                expected=str(internal_position_count),
                actual=str(actual_position_count),
                blocking=self.policy.block_on_position_mismatch,
                detail="actual position count differs from internal position count",
            ))

        actual_symbols = tuple(
            sorted(str(item).upper() for item in actual_snapshot.get("symbols_held", ()))
        )
        internal_symbols = tuple(sorted(
            str(item.get("symbol", "")).upper()
            for item in internal_positions
            if str(item.get("symbol", "")).strip()
        ))
        position_symbols_matched = actual_symbols == internal_symbols
        if not position_symbols_matched:
            issues.append(ReconciliationIssue(
                code="POSITION_SYMBOL_MISMATCH",
                expected=",".join(internal_symbols),
                actual=",".join(actual_symbols),
                blocking=self.policy.block_on_position_mismatch,
                detail="actual held symbols differ from internal held symbols",
            ))

        actual_open_orders = int(actual_snapshot.get("open_order_count", 0))
        internal_open_orders = int(internal_runtime.get("open_order_count", 0))
        open_order_count_matched = actual_open_orders == internal_open_orders
        if not open_order_count_matched:
            issues.append(ReconciliationIssue(
                code="OPEN_ORDER_COUNT_MISMATCH",
                expected=str(internal_open_orders),
                actual=str(actual_open_orders),
                blocking=self.policy.block_on_open_order_mismatch,
                detail="actual open order count differs from internal runtime state",
            ))

        actual_generation = int(
            internal_recovery.get("actual_snapshot_generation", 0)
        )
        expected_generation = int(
            internal_recovery.get("expected_snapshot_generation", 0)
        )
        recovery_generation_matched = actual_generation == expected_generation
        if not recovery_generation_matched:
            issues.append(ReconciliationIssue(
                code="RECOVERY_GENERATION_MISMATCH",
                expected=str(expected_generation),
                actual=str(actual_generation),
                blocking=self.policy.block_on_recovery_mismatch,
                detail="recovery snapshot generation is stale or unexpected",
            ))

        runtime_state = str(internal_runtime.get("runtime_state", "UNKNOWN")).upper()
        runtime_state_matched = runtime_state in {"READY", "WAITING", "STOPPED"}
        if not runtime_state_matched:
            issues.append(ReconciliationIssue(
                code="RUNTIME_STATE_MISMATCH",
                expected="READY|WAITING|STOPPED",
                actual=runtime_state,
                blocking=self.policy.block_on_runtime_state_mismatch,
                detail="internal runtime is not in an approved reconciliation state",
            ))

        blocking_count = sum(1 for item in issues if item.blocking)
        safe_mode = blocking_count > 0
        status = (
            ReconciliationStatus.MATCHED
            if not issues
            else ReconciliationStatus.SAFE_MODE
            if safe_mode
            else ReconciliationStatus.MISMATCH
        )

        return AutonomousReconciliationReport(
            status=status,
            safe_mode_engaged=safe_mode,
            autonomous_order_allowed=not safe_mode,
            issue_count=len(issues),
            blocking_issue_count=blocking_count,
            cash_matched=cash_matched,
            equity_matched=equity_matched,
            position_count_matched=position_count_matched,
            position_symbols_matched=position_symbols_matched,
            open_order_count_matched=open_order_count_matched,
            recovery_generation_matched=recovery_generation_matched,
            runtime_state_matched=runtime_state_matched,
            issues=tuple(issues),
            network_requests_executed=0,
            write_requests_executed=0,
            actual_paper_orders_submitted=0,
            live_orders_submitted=0,
        )


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))
