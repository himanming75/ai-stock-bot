from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping
import hashlib
import json


class TerminalCommitState(str, Enum):
    CONTINUE_TRACKING = "CONTINUE_TRACKING"
    COMMITTED_FILLED = "COMMITTED_FILLED"
    COMMITTED_TERMINAL_NO_FILL = "COMMITTED_TERMINAL_NO_FILL"
    DUPLICATE_COMMIT = "DUPLICATE_COMMIT"
    SAFE_MODE = "SAFE_MODE"


@dataclass(frozen=True)
class TerminalCommitIssue:
    code: str
    expected: str
    actual: str
    blocking: bool
    detail: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TerminalCommitRecord:
    commit_id: str
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
    source_result_path: str

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TerminalCommitReport:
    state: TerminalCommitState
    terminal: bool
    completion_verified: bool
    committed: bool
    duplicate_commit: bool
    next_order_allowed: bool
    safe_mode_engaged: bool
    commit_id: str
    final_status: str
    issue_count: int
    blocking_issue_count: int
    issues: tuple[TerminalCommitIssue, ...]
    completion_ledger_written: bool
    audit_ledger_written: bool
    unlock_ledger_written: bool
    recovery_snapshot_written: bool
    completion_ledger_path: str
    audit_ledger_path: str
    unlock_ledger_path: str
    recovery_snapshot_path: str
    network_requests_executed: int
    write_requests_executed: int
    actual_paper_orders_submitted: int
    live_orders_submitted: int

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "terminal": self.terminal,
            "completion_verified": self.completion_verified,
            "committed": self.committed,
            "duplicate_commit": self.duplicate_commit,
            "next_order_allowed": self.next_order_allowed,
            "safe_mode_engaged": self.safe_mode_engaged,
            "commit_id": self.commit_id,
            "final_status": self.final_status,
            "issue_count": self.issue_count,
            "blocking_issue_count": self.blocking_issue_count,
            "issues": [item.to_json_dict() for item in self.issues],
            "completion_ledger_written": self.completion_ledger_written,
            "audit_ledger_written": self.audit_ledger_written,
            "unlock_ledger_written": self.unlock_ledger_written,
            "recovery_snapshot_written": self.recovery_snapshot_written,
            "completion_ledger_path": self.completion_ledger_path,
            "audit_ledger_path": self.audit_ledger_path,
            "unlock_ledger_path": self.unlock_ledger_path,
            "recovery_snapshot_path": self.recovery_snapshot_path,
            "network_requests_executed": self.network_requests_executed,
            "write_requests_executed": self.write_requests_executed,
            "actual_paper_orders_submitted": self.actual_paper_orders_submitted,
            "live_orders_submitted": self.live_orders_submitted,
        }


class JsonlLedger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, payload: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(payload), sort_keys=True) + "\n")

    def read_all(self) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        records = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
        return tuple(records)

    def contains_commit_id(self, commit_id: str) -> bool:
        return any(
            str(item.get("commit_id", "")) == commit_id
            for item in self.read_all()
        )


class TerminalCompletionCommitter:
    ACTIVE = {
        "accepted",
        "new",
        "pending_new",
        "pending_replace",
        "held",
        "calculated",
        "partially_filled",
    }
    FILLED = {"filled"}
    TERMINAL_NO_FILL = {
        "canceled",
        "cancelled",
        "rejected",
        "expired",
        "done_for_day",
        "replaced",
    }

    def __init__(
        self,
        *,
        completion_ledger: JsonlLedger,
        audit_ledger: JsonlLedger,
        unlock_ledger: JsonlLedger,
        recovery_snapshot_path: Path,
    ) -> None:
        self.completion_ledger = completion_ledger
        self.audit_ledger = audit_ledger
        self.unlock_ledger = unlock_ledger
        self.recovery_snapshot_path = recovery_snapshot_path

    def commit(
        self,
        *,
        terminal_result: Mapping[str, Any],
        source_result_path: str,
        completed_at: str,
        network_requests_executed: int = 0,
    ) -> TerminalCommitReport:
        status = _text(
            terminal_result.get(
                "final_status",
                terminal_result.get("broker_status", ""),
            )
        ).lower()
        client_order_id = _text(terminal_result.get("client_order_id", ""))
        broker_order_id = _text(terminal_result.get("broker_order_id", ""))
        symbol = _text(terminal_result.get("symbol", "")).upper()
        side = _text(terminal_result.get("side", "")).upper()
        quantity = _text(terminal_result.get("quantity", "0"))
        filled = _text(
            terminal_result.get(
                "filled_quantity",
                terminal_result.get("final_filled_quantity", "0"),
            )
        )
        remaining = _text(
            terminal_result.get(
                "remaining_quantity",
                terminal_result.get("final_remaining_quantity", "0"),
            )
        )
        average_fill_price = _text(
            terminal_result.get("average_fill_price", "0")
        )
        position_quantity = _text(
            terminal_result.get(
                "position_quantity",
                terminal_result.get("final_position_quantity", "0"),
            )
        )
        cash = _text(terminal_result.get("cash", "0"))
        equity = _text(terminal_result.get("equity", "0"))

        issues: list[TerminalCommitIssue] = []

        if not client_order_id:
            issues.append(TerminalCommitIssue(
                code="MISSING_CLIENT_ORDER_ID",
                expected="non-empty client_order_id",
                actual="",
                blocking=True,
                detail="terminal commit requires stable order identity",
            ))

        terminal = status in self.FILLED or status in self.TERMINAL_NO_FILL
        if status in self.ACTIVE:
            return self._report(
                state=TerminalCommitState.CONTINUE_TRACKING,
                terminal=False,
                completion_verified=False,
                committed=False,
                duplicate_commit=False,
                next_order_allowed=False,
                safe_mode_engaged=False,
                commit_id="",
                final_status=status.upper(),
                issues=tuple(issues),
                network_requests_executed=network_requests_executed,
            )

        if not terminal:
            issues.append(TerminalCommitIssue(
                code="UNKNOWN_TERMINAL_STATUS",
                expected="FILLED/CANCELED/REJECTED/EXPIRED/DONE_FOR_DAY/REPLACED",
                actual=status,
                blocking=True,
                detail="unknown order status cannot be committed",
            ))

        blocking = sum(1 for item in issues if item.blocking)
        if blocking:
            return self._report(
                state=TerminalCommitState.SAFE_MODE,
                terminal=terminal,
                completion_verified=False,
                committed=False,
                duplicate_commit=False,
                next_order_allowed=False,
                safe_mode_engaged=True,
                commit_id="",
                final_status=status.upper(),
                issues=tuple(issues),
                network_requests_executed=network_requests_executed,
            )

        commit_id = self._commit_id(
            client_order_id=client_order_id,
            broker_order_id=broker_order_id,
            status=status,
            filled_quantity=filled,
            remaining_quantity=remaining,
        )

        if self.completion_ledger.contains_commit_id(commit_id):
            return self._report(
                state=TerminalCommitState.DUPLICATE_COMMIT,
                terminal=True,
                completion_verified=True,
                committed=False,
                duplicate_commit=True,
                next_order_allowed=True,
                safe_mode_engaged=False,
                commit_id=commit_id,
                final_status=status.upper(),
                issues=(),
                network_requests_executed=network_requests_executed,
            )

        record = TerminalCommitRecord(
            commit_id=commit_id,
            client_order_id=client_order_id,
            broker_order_id=broker_order_id,
            symbol=symbol,
            side=side,
            final_status=status.upper(),
            quantity=quantity,
            filled_quantity=filled,
            remaining_quantity=remaining,
            average_fill_price=average_fill_price,
            position_quantity=position_quantity,
            cash=cash,
            equity=equity,
            completed_at=completed_at,
            source_result_path=source_result_path,
        )

        completion_payload = {
            "event_type": "ORDER_COMPLETED",
            **record.to_json_dict(),
        }
        audit_payload = {
            "event_type": "TERMINAL_COMPLETION_AUDIT",
            **record.to_json_dict(),
            "verification": "PASS",
            "broker_write_performed": False,
        }
        unlock_payload = {
            "event_type": "NEXT_ORDER_UNLOCKED",
            "commit_id": commit_id,
            "client_order_id": client_order_id,
            "broker_order_id": broker_order_id,
            "final_status": status.upper(),
            "next_order_allowed": True,
            "unlocked_at": completed_at,
        }
        recovery_payload = {
            "recovery_state": "TERMINAL_COMMITTED",
            "commit_id": commit_id,
            "client_order_id": client_order_id,
            "broker_order_id": broker_order_id,
            "final_status": status.upper(),
            "next_order_allowed": True,
            "safe_mode_engaged": False,
            "completed_at": completed_at,
        }

        self.completion_ledger.append(completion_payload)
        self.audit_ledger.append(audit_payload)
        self.unlock_ledger.append(unlock_payload)
        self.recovery_snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        self.recovery_snapshot_path.write_text(
            json.dumps(recovery_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        state = (
            TerminalCommitState.COMMITTED_FILLED
            if status in self.FILLED
            else TerminalCommitState.COMMITTED_TERMINAL_NO_FILL
        )
        return self._report(
            state=state,
            terminal=True,
            completion_verified=True,
            committed=True,
            duplicate_commit=False,
            next_order_allowed=True,
            safe_mode_engaged=False,
            commit_id=commit_id,
            final_status=status.upper(),
            issues=(),
            network_requests_executed=network_requests_executed,
            completion_written=True,
            audit_written=True,
            unlock_written=True,
            recovery_written=True,
        )

    def _report(
        self,
        *,
        state: TerminalCommitState,
        terminal: bool,
        completion_verified: bool,
        committed: bool,
        duplicate_commit: bool,
        next_order_allowed: bool,
        safe_mode_engaged: bool,
        commit_id: str,
        final_status: str,
        issues: tuple[TerminalCommitIssue, ...],
        network_requests_executed: int,
        completion_written: bool = False,
        audit_written: bool = False,
        unlock_written: bool = False,
        recovery_written: bool = False,
    ) -> TerminalCommitReport:
        return TerminalCommitReport(
            state=state,
            terminal=terminal,
            completion_verified=completion_verified,
            committed=committed,
            duplicate_commit=duplicate_commit,
            next_order_allowed=next_order_allowed,
            safe_mode_engaged=safe_mode_engaged,
            commit_id=commit_id,
            final_status=final_status,
            issue_count=len(issues),
            blocking_issue_count=sum(1 for item in issues if item.blocking),
            issues=issues,
            completion_ledger_written=completion_written,
            audit_ledger_written=audit_written,
            unlock_ledger_written=unlock_written,
            recovery_snapshot_written=recovery_written,
            completion_ledger_path=str(self.completion_ledger.path),
            audit_ledger_path=str(self.audit_ledger.path),
            unlock_ledger_path=str(self.unlock_ledger.path),
            recovery_snapshot_path=str(self.recovery_snapshot_path),
            network_requests_executed=network_requests_executed,
            write_requests_executed=0,
            actual_paper_orders_submitted=0,
            live_orders_submitted=0,
        )

    @staticmethod
    def _commit_id(
        *,
        client_order_id: str,
        broker_order_id: str,
        status: str,
        filled_quantity: str,
        remaining_quantity: str,
    ) -> str:
        raw = "|".join([
            client_order_id,
            broker_order_id,
            status,
            filled_quantity,
            remaining_quantity,
        ])
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _text(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "value"):
        value = value.value
    return str(value).strip()
