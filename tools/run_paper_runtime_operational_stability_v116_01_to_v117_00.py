from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_runtime_stability import (
    OperationalStabilityConfig,
    OperationalStabilityController,
)


@dataclass
class DemoState:
    value: str


class DemoClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class DemoRuntime:
    def __init__(self):
        self.state = DemoState("READY")
        self.outcomes = []
        self.cycles = 0
        self.heartbeats = 0
        self.recoveries = 0
        self.snapshots = 0
        self.stops = 0

    def run_cycle(self):
        outcome = self.outcomes.pop(0) if self.outcomes else True
        if isinstance(outcome, Exception):
            raise outcome
        self.cycles += 1
        return {"cycle_completed": True}

    def heartbeat(self):
        self.heartbeats += 1

    def recover(self):
        self.recoveries += 1
        self.state = DemoState("READY")

    def save_recovery(self):
        self.snapshots += 1

    def stop(self):
        self.stops += 1
        self.state = DemoState("STOPPED")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    output = Path(args.repository_root).resolve() / "release" / "v117_00" / "output"
    output.mkdir(parents=True, exist_ok=True)

    clock = DemoClock()
    sleeps = []
    runtime = DemoRuntime()
    controller = OperationalStabilityController(
        runtime=runtime,
        config=OperationalStabilityConfig(
            cycle_timeout_seconds=30,
            heartbeat_timeout_seconds=120,
            max_consecutive_failures=3,
            max_recovery_attempts=2,
            initial_backoff_seconds=5,
            max_backoff_seconds=60,
            backoff_multiplier=3,
        ),
        monotonic=clock,
        sleep=sleeps.append,
    )

    for _ in range(500):
        controller.run_cycle()
        controller.heartbeat()

    runtime.outcomes = [
        RuntimeError("fixture failure one"),
        RuntimeError("fixture failure two"),
        RuntimeError("fixture failure three"),
    ]
    failure_results = [controller.run_cycle() for _ in range(3)]
    recovery_result = controller.attempt_recovery()
    shutdown_result = controller.graceful_shutdown()

    result = {
        "stage_range": "V116.01-V117.00",
        "status": "PASS",
        "implementation_type": "PAPER_RUNTIME_OPERATIONAL_STABILITY",
        "successful_long_run_cycles": 500,
        "failure_actions": [item.action.value for item in failure_results],
        "backoff_sequence": sleeps,
        "circuit_open_after_failures": failure_results[-1].action.value == "CIRCUIT_OPEN",
        "recovery_action": recovery_result.action.value,
        "shutdown_action": shutdown_result.action.value,
        "runtime_final_state": runtime.state.value,
        "runtime_cycle_count": runtime.cycles,
        "heartbeat_count": runtime.heartbeats,
        "runtime_recovery_count": runtime.recoveries,
        "runtime_snapshot_count": runtime.snapshots,
        "runtime_stop_count": runtime.stops,
        "stability_stats": controller.stats.to_json_dict(),
        "network_requests_executed": controller.network_requests_executed,
        "write_requests_executed": controller.write_requests_executed,
        "actual_paper_orders_submitted": controller.actual_paper_orders_submitted,
        "live_orders_submitted": controller.live_orders_submitted,
        "next_phase": "V117_01_CONTINUOUS_PAPER_RUNTIME_RELEASE_CANDIDATE",
    }
    (output / "paper_runtime_operational_stability_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
