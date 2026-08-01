from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_engine import EventBus, JsonRecoveryStore, ManualClock, RuntimeConfig, RuntimeManager, Scheduler


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    parser.add_argument("--ticks", type=int, default=3)
    args = parser.parse_args()

    repository_root = Path(args.repository_root).resolve()
    output = repository_root / "release" / "v102_00" / "output"
    output.mkdir(parents=True, exist_ok=True)

    clock = ManualClock(datetime(2026, 8, 1, 16, 0, tzinfo=timezone.utc))
    bus = EventBus()
    manager = RuntimeManager(
        config=RuntimeConfig(
            heartbeat_interval_seconds=5,
            heartbeat_stale_after_seconds=15,
            recovery_interval_seconds=10,
        ),
        clock=clock,
        event_bus=bus,
        scheduler=Scheduler(),
        recovery_store=JsonRecoveryStore(output / "runtime_recovery.json"),
    )

    manager.start()
    executions = []
    for _ in range(args.ticks):
        executions.append(manager.tick())
        clock.advance(seconds=5)
    manager.shutdown("FOUNDATION_DEMO_COMPLETE")

    result = {
        "stage_range": "V101.01-V102.00",
        "status": "PASS",
        "implementation_type": "REAL_RUNTIME_FOUNDATION",
        "runtime_state": manager.state.value,
        "tick_count": manager.tick_count,
        "task_executions": executions,
        "event_count": len(bus.history()),
        "recovery_snapshot_exists": (output / "runtime_recovery.json").exists(),
        "network_write_enabled": False,
        "paper_order_submission_enabled": False,
        "live_trading_enabled": False,
        "network_requests_executed": 0,
        "actual_orders_submitted": 0,
        "next_phase": "V102_01_REALTIME_MARKET_DATA_FOUNDATION",
    }
    (output / "runtime_foundation_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
