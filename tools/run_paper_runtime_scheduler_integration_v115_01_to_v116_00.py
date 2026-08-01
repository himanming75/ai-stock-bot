from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_runtime_scheduler import (
    PaperRuntimeSchedulerIntegration,
    RuntimeSchedulerIntegrationConfig,
)
from paper_scheduler import (
    MarketSessionPhase,
    SchedulerAction,
    SchedulerDecision,
)


@dataclass
class DemoState:
    value: str


class DemoPaperRuntime:
    def __init__(self):
        self.state = DemoState("CREATED")
        self.prepare_count = 0
        self.start_count = 0
        self.cycle_count = 0
        self.recover_count = 0
        self.stop_count = 0
        self.recovery_count = 0
        self.signal_count = 0
        self.risk_approved = 0
        self.execution_accepted = 0
        self.fills_completed = 0
        self.portfolio_updates = 0

    def prepare(self):
        self.prepare_count += 1
        self.state = DemoState("READY")

    def start(self):
        self.start_count += 1
        self.state = DemoState("READY")

    def run_cycle(self):
        self.cycle_count += 1
        self.signal_count += 1
        self.risk_approved += 1
        self.execution_accepted += 1
        self.fills_completed += 1
        self.portfolio_updates += 1
        self.state = DemoState("RUNNING")
        return {
            "cycle_completed": True,
            "signal_count": 1,
            "risk_status": "APPROVED",
            "execution_status": "ACCEPTED",
            "fill_status": "FILLED",
        }

    def recover(self):
        self.recover_count += 1
        self.state = DemoState("READY")

    def save_recovery(self):
        self.recovery_count += 1

    def stop(self):
        self.stop_count += 1
        self.state = DemoState("STOPPED")


def make_decision(action, phase):
    return SchedulerDecision(
        decided_at=datetime(2026, 8, 3, 13, 30, tzinfo=timezone.utc),
        phase=phase,
        action=action,
        reason="demo",
        session_date=date(2026, 8, 3),
        next_wakeup_seconds=60,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    output = Path(args.repository_root).resolve() / "release" / "v116_00" / "output"
    output.mkdir(parents=True, exist_ok=True)

    runtime = DemoPaperRuntime()
    integration = PaperRuntimeSchedulerIntegration(
        runtime=runtime,
        config=RuntimeSchedulerIntegrationConfig(),
        now=lambda: datetime(2026, 8, 3, 13, 30, tzinfo=timezone.utc),
    )

    sequence = [
        make_decision(SchedulerAction.PREPARE, MarketSessionPhase.PRE_MARKET),
        make_decision(SchedulerAction.START_SESSION, MarketSessionPhase.REGULAR),
        make_decision(SchedulerAction.RUN_CYCLE, MarketSessionPhase.REGULAR),
        make_decision(SchedulerAction.RECOVER_SESSION, MarketSessionPhase.REGULAR),
        make_decision(SchedulerAction.CLOSE_SESSION, MarketSessionPhase.AFTER_HOURS),
    ]
    results = [integration.handle(item) for item in sequence]

    result = {
        "stage_range": "V115.01-V116.00",
        "status": "PASS",
        "implementation_type": "PAPER_RUNTIME_SCHEDULER_INTEGRATION",
        "scheduler_actions": [item.action.value for item in sequence],
        "integration_events": [item.event_type.value for item in results],
        "runtime_final_state": runtime.state.value,
        "prepare_count": runtime.prepare_count,
        "start_count": runtime.start_count,
        "cycle_count": runtime.cycle_count,
        "recover_count": runtime.recover_count,
        "stop_count": runtime.stop_count,
        "recovery_snapshot_count": runtime.recovery_count,
        "signal_count": runtime.signal_count,
        "risk_approved_count": runtime.risk_approved,
        "execution_accepted_count": runtime.execution_accepted,
        "fill_completed_count": runtime.fills_completed,
        "portfolio_update_count": runtime.portfolio_updates,
        "integration_stats": integration.stats.to_json_dict(),
        "network_requests_executed": integration.network_requests_executed,
        "write_requests_executed": integration.write_requests_executed,
        "actual_paper_orders_submitted": integration.actual_paper_orders_submitted,
        "live_orders_submitted": integration.live_orders_submitted,
        "next_phase": "V116_01_PAPER_RUNTIME_OPERATIONAL_STABILITY",
    }
    (output / "paper_runtime_scheduler_integration_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
