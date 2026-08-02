from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .lifecycle_monitor import (
    ExistingPaperOrderLifecycleMonitor,
    LifecycleLedger,
    LifecycleMonitorReport,
    LifecycleSnapshot,
)
from .terminal_commit import (
    JsonlLedger,
    TerminalCommitReport,
    TerminalCommitState,
    TerminalCompletionCommitter,
)


@dataclass(frozen=True)
class TerminalMonitorCommitOrchestratorReport:
    monitor_report: LifecycleMonitorReport
    commit_report: TerminalCommitReport
    terminal_observed: bool
    commit_attempted: bool
    terminal_committed: bool
    next_order_allowed: bool
    safe_mode_engaged: bool

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "monitor_report": self.monitor_report.to_json_dict(),
            "commit_report": self.commit_report.to_json_dict(),
            "terminal_observed": self.terminal_observed,
            "commit_attempted": self.commit_attempted,
            "terminal_committed": self.terminal_committed,
            "next_order_allowed": self.next_order_allowed,
            "safe_mode_engaged": self.safe_mode_engaged,
        }


class TerminalMonitorCommitOrchestrator:
    def __init__(
        self,
        *,
        lifecycle_ledger_path: Path,
        completion_ledger_path: Path,
        audit_ledger_path: Path,
        unlock_ledger_path: Path,
        recovery_snapshot_path: Path,
    ) -> None:
        self.monitor = ExistingPaperOrderLifecycleMonitor(
            ledger=LifecycleLedger(lifecycle_ledger_path)
        )
        self.committer = TerminalCompletionCommitter(
            completion_ledger=JsonlLedger(completion_ledger_path),
            audit_ledger=JsonlLedger(audit_ledger_path),
            unlock_ledger=JsonlLedger(unlock_ledger_path),
            recovery_snapshot_path=recovery_snapshot_path,
        )

    def run(
        self,
        *,
        poller: Callable[[int], LifecycleSnapshot],
        max_polls: int,
        poll_interval_seconds: float = 0.0,
        network_requests_per_poll: int = 3,
        source_result_path: str = "",
    ) -> TerminalMonitorCommitOrchestratorReport:
        monitor_report = self.monitor.monitor(
            poller=poller,
            max_polls=max_polls,
            poll_interval_seconds=poll_interval_seconds,
            stop_on_material_transition=False,
            network_requests_per_poll=network_requests_per_poll,
        )
        final = monitor_report.snapshots[-1]

        final_status_for_commit = (
            "MONITOR_SAFE_MODE"
            if monitor_report.safe_mode_engaged
            else final.status
        )
        commit_report = self.committer.commit(
            terminal_result={
                "client_order_id": final.client_order_id,
                "broker_order_id": final.broker_order_id,
                "symbol": final.symbol,
                "side": final.side,
                "final_status": final_status_for_commit,
                "quantity": str(final.quantity),
                "filled_quantity": str(final.filled_quantity),
                "remaining_quantity": str(final.remaining_quantity),
                "average_fill_price": str(final.average_fill_price),
                "position_quantity": str(final.position_quantity),
                "cash": str(final.cash),
                "equity": str(final.equity),
            },
            source_result_path=source_result_path,
            completed_at=(
                datetime.now(timezone.utc).isoformat()
                if monitor_report.terminal
                else ""
            ),
            network_requests_executed=monitor_report.network_requests_executed,
        )

        terminal_observed = monitor_report.terminal
        commit_attempted = terminal_observed
        terminal_committed = (
            commit_report.committed
            or commit_report.duplicate_commit
        )
        safe_mode = (
            monitor_report.safe_mode_engaged
            or commit_report.safe_mode_engaged
        )

        return TerminalMonitorCommitOrchestratorReport(
            monitor_report=monitor_report,
            commit_report=commit_report,
            terminal_observed=terminal_observed,
            commit_attempted=commit_attempted,
            terminal_committed=terminal_committed,
            next_order_allowed=commit_report.next_order_allowed,
            safe_mode_engaged=safe_mode,
        )
