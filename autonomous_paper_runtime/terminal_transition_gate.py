from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from datetime import datetime, timezone

from .lifecycle_monitor import (
    ExistingPaperOrderLifecycleMonitor,
    LifecycleLedger,
    LifecycleMonitorReport,
    LifecycleSnapshot,
)
from .completion_unlock_gate import (
    CompletionLedger,
    CompletionUnlockReport,
    OrderCompletionNextOrderUnlockGate,
)


@dataclass(frozen=True)
class TerminalTransitionGateReport:
    monitor_report: LifecycleMonitorReport
    completion_report: CompletionUnlockReport
    terminal_transition_observed: bool
    unlock_evaluated: bool
    new_order_allowed: bool
    safe_mode_engaged: bool

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "monitor_report": self.monitor_report.to_json_dict(),
            "completion_report": self.completion_report.to_json_dict(),
            "terminal_transition_observed": self.terminal_transition_observed,
            "unlock_evaluated": self.unlock_evaluated,
            "new_order_allowed": self.new_order_allowed,
            "safe_mode_engaged": self.safe_mode_engaged,
        }


class ContinuedActualOrderMonitorTerminalTransitionGate:
    def __init__(
        self,
        *,
        lifecycle_ledger_path: Path,
        completion_ledger_path: Path,
    ) -> None:
        self.monitor = ExistingPaperOrderLifecycleMonitor(
            ledger=LifecycleLedger(lifecycle_ledger_path)
        )
        self.completion_gate = OrderCompletionNextOrderUnlockGate(
            ledger=CompletionLedger(completion_ledger_path)
        )

    def run(
        self,
        *,
        poller: Callable[[int], LifecycleSnapshot],
        max_polls: int,
        poll_interval_seconds: float = 0.0,
        network_requests_per_poll: int = 3,
    ) -> TerminalTransitionGateReport:
        monitor_report = self.monitor.monitor(
            poller=poller,
            max_polls=max_polls,
            poll_interval_seconds=poll_interval_seconds,
            stop_on_material_transition=False,
            network_requests_per_poll=network_requests_per_poll,
        )

        final = monitor_report.snapshots[-1]
        completion_report = self.completion_gate.evaluate(
            lifecycle_result={
                "client_order_id": final.client_order_id,
                "broker_order_id": final.broker_order_id,
                "symbol": final.symbol,
                "side": final.side,
                "final_status": final.status,
                "quantity": str(final.quantity),
                "final_filled_quantity": str(final.filled_quantity),
                "final_remaining_quantity": str(final.remaining_quantity),
                "final_position_quantity": str(final.position_quantity),
                "average_fill_price": str(final.average_fill_price),
                "cash": str(final.cash),
                "equity": str(final.equity),
            },
            completed_at=(
                datetime.now(timezone.utc).isoformat()
                if monitor_report.terminal
                else ""
            ),
            network_requests_executed=monitor_report.network_requests_executed,
        )

        terminal_transition_observed = monitor_report.terminal
        return TerminalTransitionGateReport(
            monitor_report=monitor_report,
            completion_report=completion_report,
            terminal_transition_observed=terminal_transition_observed,
            unlock_evaluated=True,
            new_order_allowed=completion_report.new_order_allowed,
            safe_mode_engaged=(
                monitor_report.safe_mode_engaged
                or completion_report.safe_mode_engaged
            ),
        )
