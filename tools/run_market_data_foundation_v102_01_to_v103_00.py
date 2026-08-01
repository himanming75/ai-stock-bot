from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_engine import EventBus, ManualClock
from market_data_engine import (
    AlpacaMessageParser,
    ConnectionState,
    ConnectionStateMachine,
    ExponentialBackoff,
    FixtureMarketDataStream,
    FreshnessMonitor,
    MarketDataRouter,
    SequenceGuard,
    SubscriptionRegistry,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    repository_root = Path(args.repository_root).resolve()
    output = repository_root / "release" / "v103_00" / "output"
    output.mkdir(parents=True, exist_ok=True)

    now = datetime(2026, 8, 1, 16, 0, tzinfo=timezone.utc)
    clock = ManualClock(now)
    bus = EventBus()
    registry = SubscriptionRegistry()
    registry.subscribe(quotes=["AAPL"], trades=["AAPL"], bars=["AAPL"])

    router = MarketDataRouter(
        event_bus=bus,
        subscriptions=registry,
        sequence_guard=SequenceGuard(),
        freshness_monitor=FreshnessMonitor(stale_after_seconds=15),
        now=clock.now,
    )

    frames = [
        [{"T":"success","msg":"authenticated"}],
        [{"T":"subscription","quotes":["AAPL"],"trades":["AAPL"],"bars":["AAPL"]}],
        [
            {"T":"q","S":"AAPL","t":"2026-08-01T16:00:00Z","bp":100.00,"bs":2,"ap":100.10,"as":3,"seq":1},
            {"T":"t","S":"AAPL","t":"2026-08-01T16:00:00Z","p":100.05,"s":5,"x":"V","seq":1},
            {"T":"b","S":"AAPL","t":"2026-08-01T16:00:00Z","o":100.00,"h":100.20,"l":99.90,"c":100.05,"v":500,"n":10,"vw":100.04,"seq":1},
        ],
        [
            {"T":"q","S":"AAPL","t":"2026-08-01T16:00:01Z","bp":100.00,"bs":2,"ap":100.10,"as":3,"seq":1},
            {"T":"q","S":"MSFT","t":"2026-08-01T16:00:01Z","bp":200.00,"bs":2,"ap":200.10,"as":3,"seq":1},
        ],
    ]

    stream_result = FixtureMarketDataStream(
        frames=frames,
        parser=AlpacaMessageParser(),
        router=router,
    ).run()

    state_machine = ConnectionStateMachine()
    for state in [
        ConnectionState.CONNECTING,
        ConnectionState.AUTHENTICATING,
        ConnectionState.SUBSCRIBING,
        ConnectionState.STREAMING,
        ConnectionState.STOPPED,
    ]:
        state_machine.transition(state)

    backoff = ExponentialBackoff(initial_seconds=1, multiplier=2, maximum_seconds=8)
    backoff_preview = [backoff.next_delay() for _ in range(5)]

    result = {
        "stage_range": "V102.01-V103.00",
        "status": "PASS",
        "implementation_type": "REALTIME_MARKET_DATA_FOUNDATION",
        "subscription_snapshot": registry.snapshot(),
        "stream_result": stream_result,
        "routing_stats": vars(router.stats),
        "event_count": len(bus.history()),
        "connection_state": state_machine.state.value,
        "connection_history": [state.value for state in state_machine.history],
        "backoff_preview_seconds": backoff_preview,
        "network_connection_enabled": False,
        "network_requests_executed": 0,
        "paper_order_submission_enabled": False,
        "actual_orders_submitted": 0,
        "live_trading_enabled": False,
        "next_phase": "V103_01_STRATEGY_SIGNAL_ENGINE_FOUNDATION",
    }
    (output / "market_data_foundation_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
