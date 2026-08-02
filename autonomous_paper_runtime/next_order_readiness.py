from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Mapping, Sequence
import json


class NextOrderReadinessState(str, Enum):
    READY = "READY"
    BLOCKED_ACTIVE_ORDER = "BLOCKED_ACTIVE_ORDER"
    BLOCKED_TERMINAL_NOT_COMMITTED = "BLOCKED_TERMINAL_NOT_COMMITTED"
    BLOCKED_OPEN_ORDER = "BLOCKED_OPEN_ORDER"
    BLOCKED_ACCOUNT = "BLOCKED_ACCOUNT"
    BLOCKED_MARKET_CLOSED = "BLOCKED_MARKET_CLOSED"
    BLOCKED_RISK = "BLOCKED_RISK"
    BLOCKED_EXPOSURE = "BLOCKED_EXPOSURE"
    SAFE_MODE = "SAFE_MODE"


@dataclass(frozen=True)
class ReadinessIssue:
    code: str
    expected: str
    actual: str
    blocking: bool
    detail: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NextOrderReadinessReport:
    state: NextOrderReadinessState
    ready: bool
    next_order_allowed: bool
    safe_mode_engaged: bool
    active_order_present: bool
    terminal_commit_verified: bool
    open_order_count: int
    account_active: bool
    trading_blocked: bool
    market_is_open: bool
    risk_approved: bool
    position_count: int
    total_market_value: str
    issue_count: int
    blocking_issue_count: int
    issues: tuple[ReadinessIssue, ...]
    readiness_snapshot_written: bool
    readiness_snapshot_path: str
    network_requests_executed: int
    write_requests_executed: int
    actual_paper_orders_submitted: int
    live_orders_submitted: int

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "ready": self.ready,
            "next_order_allowed": self.next_order_allowed,
            "safe_mode_engaged": self.safe_mode_engaged,
            "active_order_present": self.active_order_present,
            "terminal_commit_verified": self.terminal_commit_verified,
            "open_order_count": self.open_order_count,
            "account_active": self.account_active,
            "trading_blocked": self.trading_blocked,
            "market_is_open": self.market_is_open,
            "risk_approved": self.risk_approved,
            "position_count": self.position_count,
            "total_market_value": self.total_market_value,
            "issue_count": self.issue_count,
            "blocking_issue_count": self.blocking_issue_count,
            "issues": [item.to_json_dict() for item in self.issues],
            "readiness_snapshot_written": self.readiness_snapshot_written,
            "readiness_snapshot_path": self.readiness_snapshot_path,
            "network_requests_executed": self.network_requests_executed,
            "write_requests_executed": self.write_requests_executed,
            "actual_paper_orders_submitted": self.actual_paper_orders_submitted,
            "live_orders_submitted": self.live_orders_submitted,
        }


class AutonomousNextOrderReadinessGate:
    def __init__(self, *, readiness_snapshot_path: Path) -> None:
        self.readiness_snapshot_path = readiness_snapshot_path

    def evaluate(
        self,
        *,
        terminal_monitor_result: Mapping[str, Any],
        account: Mapping[str, Any],
        open_orders: Sequence[Mapping[str, Any]],
        positions: Sequence[Mapping[str, Any]],
        market_is_open: bool,
        risk_approved: bool,
        max_positions: int,
        max_total_market_value: Decimal,
        network_requests_executed: int = 0,
    ) -> NextOrderReadinessReport:
        if max_positions < 0:
            raise ValueError("max_positions cannot be negative")
        if max_total_market_value < 0:
            raise ValueError("max_total_market_value cannot be negative")

        issues: list[ReadinessIssue] = []

        monitor = terminal_monitor_result.get(
            "monitor_report",
            terminal_monitor_result,
        )
        commit = terminal_monitor_result.get(
            "commit_report",
            terminal_monitor_result,
        )

        final_status = _text(
            monitor.get("final_status", commit.get("final_status", ""))
        ).upper()
        terminal_observed = bool(
            terminal_monitor_result.get(
                "terminal_observed",
                monitor.get("terminal", False),
            )
        )
        terminal_committed = bool(
            terminal_monitor_result.get(
                "terminal_committed",
                commit.get("committed", False)
                or commit.get("duplicate_commit", False),
            )
        )
        monitor_safe_mode = bool(
            terminal_monitor_result.get(
                "safe_mode_engaged",
                monitor.get("safe_mode_engaged", False)
                or commit.get("safe_mode_engaged", False),
            )
        )

        active_order_present = (
            final_status in {
                "ACCEPTED",
                "NEW",
                "PENDING_NEW",
                "PENDING_REPLACE",
                "HELD",
                "CALCULATED",
                "PARTIALLY_FILLED",
            }
            or len(open_orders) > 0
        )

        account_status = _text(account.get("status", "")).upper()
        account_active = account_status == "ACTIVE"
        trading_blocked = _bool(account.get("trading_blocked", False))

        total_market_value = sum(
            (_decimal(item.get("market_value", "0")) for item in positions),
            Decimal("0"),
        )
        position_count = len(positions)

        if monitor_safe_mode:
            issues.append(ReadinessIssue(
                code="UPSTREAM_SAFE_MODE",
                expected="safe_mode=false",
                actual="true",
                blocking=True,
                detail="upstream lifecycle or terminal commit entered Safe Mode",
            ))

        if active_order_present:
            issues.append(ReadinessIssue(
                code="ACTIVE_ORDER_PRESENT",
                expected="no active or open orders",
                actual=f"status={final_status}, open_orders={len(open_orders)}",
                blocking=True,
                detail="a new autonomous order cannot start while another order is active",
            ))

        if terminal_observed and not terminal_committed:
            issues.append(ReadinessIssue(
                code="TERMINAL_NOT_COMMITTED",
                expected="terminal_committed=true",
                actual="false",
                blocking=True,
                detail="terminal order must be durably committed before next-order readiness",
            ))

        if not account_active:
            issues.append(ReadinessIssue(
                code="ACCOUNT_NOT_ACTIVE",
                expected="ACTIVE",
                actual=account_status,
                blocking=True,
                detail="broker account is not active",
            ))

        if trading_blocked:
            issues.append(ReadinessIssue(
                code="TRADING_BLOCKED",
                expected="false",
                actual="true",
                blocking=True,
                detail="broker account reports trading_blocked",
            ))

        if not market_is_open:
            issues.append(ReadinessIssue(
                code="MARKET_CLOSED",
                expected="market_is_open=true",
                actual="false",
                blocking=True,
                detail="next autonomous order must not start while market is closed",
            ))

        if not risk_approved:
            issues.append(ReadinessIssue(
                code="RISK_NOT_APPROVED",
                expected="risk_approved=true",
                actual="false",
                blocking=True,
                detail="runtime risk gate did not approve another order",
            ))

        if position_count > max_positions:
            issues.append(ReadinessIssue(
                code="MAX_POSITIONS_EXCEEDED",
                expected=f"<={max_positions}",
                actual=str(position_count),
                blocking=True,
                detail="current portfolio exceeds allowed position count",
            ))

        if total_market_value > max_total_market_value:
            issues.append(ReadinessIssue(
                code="MAX_MARKET_VALUE_EXCEEDED",
                expected=f"<={max_total_market_value}",
                actual=str(total_market_value),
                blocking=True,
                detail="current portfolio exposure exceeds configured cap",
            ))

        blocking = sum(1 for item in issues if item.blocking)
        safe_mode = monitor_safe_mode

        if safe_mode:
            state = NextOrderReadinessState.SAFE_MODE
        elif active_order_present:
            state = NextOrderReadinessState.BLOCKED_ACTIVE_ORDER
        elif terminal_observed and not terminal_committed:
            state = NextOrderReadinessState.BLOCKED_TERMINAL_NOT_COMMITTED
        elif len(open_orders) > 0:
            state = NextOrderReadinessState.BLOCKED_OPEN_ORDER
        elif not account_active or trading_blocked:
            state = NextOrderReadinessState.BLOCKED_ACCOUNT
        elif not market_is_open:
            state = NextOrderReadinessState.BLOCKED_MARKET_CLOSED
        elif not risk_approved:
            state = NextOrderReadinessState.BLOCKED_RISK
        elif (
            position_count > max_positions
            or total_market_value > max_total_market_value
        ):
            state = NextOrderReadinessState.BLOCKED_EXPOSURE
        else:
            state = NextOrderReadinessState.READY

        ready = state == NextOrderReadinessState.READY
        snapshot = {
            "state": state.value,
            "ready": ready,
            "next_order_allowed": ready,
            "safe_mode_engaged": safe_mode,
            "active_order_present": active_order_present,
            "terminal_commit_verified": terminal_committed,
            "open_order_count": len(open_orders),
            "account_active": account_active,
            "trading_blocked": trading_blocked,
            "market_is_open": market_is_open,
            "risk_approved": risk_approved,
            "position_count": position_count,
            "total_market_value": str(total_market_value),
            "issue_count": len(issues),
            "blocking_issue_count": blocking,
            "issues": [item.to_json_dict() for item in issues],
        }

        self.readiness_snapshot_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        self.readiness_snapshot_path.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        return NextOrderReadinessReport(
            state=state,
            ready=ready,
            next_order_allowed=ready,
            safe_mode_engaged=safe_mode,
            active_order_present=active_order_present,
            terminal_commit_verified=terminal_committed,
            open_order_count=len(open_orders),
            account_active=account_active,
            trading_blocked=trading_blocked,
            market_is_open=market_is_open,
            risk_approved=risk_approved,
            position_count=position_count,
            total_market_value=str(total_market_value),
            issue_count=len(issues),
            blocking_issue_count=blocking,
            issues=tuple(issues),
            readiness_snapshot_written=True,
            readiness_snapshot_path=str(self.readiness_snapshot_path),
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


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}
