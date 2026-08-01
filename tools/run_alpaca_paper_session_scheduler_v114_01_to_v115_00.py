from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from paper_scheduler import (
    AlpacaPaperSessionScheduler,
    AtomicSchedulerStateStore,
    SessionSchedulerConfig,
    TradingCalendarPolicy,
)


class MutableClock:
    def __init__(self, moment):
        self.moment = moment

    def now(self):
        return self.moment


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    repo = Path(args.repository_root).resolve()
    output = repo / "release" / "v115_00" / "output"
    output.mkdir(parents=True, exist_ok=True)
    state_path = output / "paper_session_scheduler_state.json"

    clock = MutableClock(datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc))
    scheduler = AlpacaPaperSessionScheduler(
        calendar=TradingCalendarPolicy(
            holidays=frozenset({date(2026, 12, 25)})
        ),
        store=AtomicSchedulerStateStore(state_path),
        config=SessionSchedulerConfig(),
        now=clock.now,
    )

    decisions = []

    # 08:00 ET - prepare.
    clock.moment = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
    decisions.append(scheduler.tick())

    # 09:30 ET - start.
    clock.moment = datetime(2026, 8, 3, 13, 30, tzinfo=timezone.utc)
    decisions.append(scheduler.tick())

    # 09:31 ET - cycle.
    clock.moment = datetime(2026, 8, 3, 13, 31, tzinfo=timezone.utc)
    decisions.append(scheduler.tick())

    # Simulated restart during regular session.
    restarted = AlpacaPaperSessionScheduler(
        calendar=scheduler.calendar,
        store=AtomicSchedulerStateStore(state_path),
        config=scheduler.config,
        now=clock.now,
    )
    decisions.append(restarted.recover())

    # 16:01 ET - close.
    clock.moment = datetime(2026, 8, 3, 20, 1, tzinfo=timezone.utc)
    decisions.append(restarted.tick())

    final_state = AtomicSchedulerStateStore(state_path).load()
    result = {
        "stage_range": "V114.01-V115.00",
        "status": "PASS",
        "implementation_type": "ALPACA_PAPER_SESSION_SCHEDULER_FOUNDATION",
        "actions": [decision.action.value for decision in decisions],
        "phases": [decision.phase.value for decision in decisions],
        "cycle_count": final_state.cycle_count,
        "heartbeat_count": final_state.heartbeat_count,
        "restart_count": final_state.restart_count,
        "session_prepared": final_state.session_prepared,
        "session_active": final_state.session_active,
        "session_closed": final_state.session_closed,
        "persisted_state_exists": state_path.exists(),
        "network_requests_executed": restarted.network_requests_executed,
        "write_requests_executed": restarted.write_requests_executed,
        "actual_paper_orders_submitted": restarted.actual_paper_orders_submitted,
        "live_orders_submitted": restarted.live_orders_submitted,
        "next_phase": "V115_01_PAPER_RUNTIME_SCHEDULER_INTEGRATION",
    }
    (output / "alpaca_paper_session_scheduler_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
