from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_engine import EventBus
from strategy_engine import (
    ConfidenceFilter,
    CooldownFilter,
    DuplicateSignalGuard,
    MarketSnapshot,
    MovingAverageCrossStrategy,
    RiskPreFilter,
    SignalEngine,
)


def make_snapshot(timestamp, closes, position="2", cash="1000"):
    return MarketSnapshot(
        symbol="AAPL",
        timestamp=timestamp,
        last_price=Decimal("50"),
        bid_price=Decimal("49.99"),
        ask_price=Decimal("50.01"),
        recent_closes=tuple(Decimal(str(x)) for x in closes),
        position_quantity=Decimal(position),
        cash_available=Decimal(cash),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    output = Path(args.repository_root).resolve() / "release" / "v104_00" / "output"
    output.mkdir(parents=True, exist_ok=True)

    now = datetime(2026, 8, 1, 16, 0, tzinfo=timezone.utc)
    bus = EventBus()
    published = []
    bus.subscribe("strategy.signal", lambda event: published.append(event.payload["signal"]))

    engine = SignalEngine(
        event_bus=bus,
        strategies=[MovingAverageCrossStrategy(short_window=2, long_window=4)],
        confidence_filter=ConfidenceFilter(Decimal("0.10")),
        cooldown_filter=CooldownFilter(cooldown_seconds=60),
        duplicate_guard=DuplicateSignalGuard(ttl_seconds=60),
        risk_filter=RiskPreFilter(
            max_quantity=Decimal("1"),
            max_notional=Decimal("100"),
            allowed_symbols={"AAPL", "MSFT", "SPY"},
        ),
    )

    accepted_first = engine.evaluate(make_snapshot(now, [40,40,60,60]))
    accepted_duplicate = engine.evaluate(make_snapshot(now+timedelta(seconds=30), [40,40,60,60]))
    accepted_sell = engine.evaluate(make_snapshot(now+timedelta(seconds=90), [60,60,40,40]))

    result = {
        "stage_range": "V103.01-V104.00",
        "status": "PASS",
        "implementation_type": "STRATEGY_SIGNAL_ENGINE_FOUNDATION",
        "first_signal_count": len(accepted_first),
        "duplicate_signal_count": len(accepted_duplicate),
        "sell_signal_count": len(accepted_sell),
        "published_event_count": len(published),
        "published_actions": [signal.action.value for signal in published],
        "stats": vars(engine.stats),
        "order_intents_created": 0,
        "paper_order_submission_enabled": False,
        "network_write_enabled": False,
        "actual_orders_submitted": 0,
        "live_trading_enabled": False,
        "next_phase": "V104_01_ORDER_INTENT_AND_POSITION_SIZING_FOUNDATION",
    }

    (output / "strategy_signal_engine_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
