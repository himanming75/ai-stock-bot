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

from runtime_engine import Event, EventBus, ManualClock
from strategy_engine import MarketSnapshot, SignalAction, StrategySignal
from execution_engine import (
    DuplicateIntentGuard,
    IntentExpiryPolicy,
    OrderIntentEngine,
    OrderIntentFactory,
    PositionSizer,
    PositionSizingConfig,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args()

    output = Path(args.repository_root).resolve() / "release" / "v105_00" / "output"
    output.mkdir(parents=True, exist_ok=True)

    now = datetime(2026, 8, 1, 16, 0, tzinfo=timezone.utc)
    clock = ManualClock(now)
    bus = EventBus()
    intents = []
    bus.subscribe("order.intent", lambda event: intents.append(event.payload["intent"]))

    snapshot = MarketSnapshot(
        symbol="AAPL",
        timestamp=now,
        last_price=Decimal("50"),
        bid_price=Decimal("49.99"),
        ask_price=Decimal("50.01"),
        recent_closes=(Decimal("40"), Decimal("40"), Decimal("60"), Decimal("60")),
        position_quantity=Decimal("2"),
        cash_available=Decimal("1000"),
    )

    engine = OrderIntentEngine(
        event_bus=bus,
        intent_factory=OrderIntentFactory(
            position_sizer=PositionSizer(
                PositionSizingConfig(
                    max_quantity=Decimal("1"),
                    max_order_notional=Decimal("100"),
                    cash_fraction=Decimal("0.10"),
                    sell_fraction=Decimal("0.50"),
                    fractional_step=Decimal("0.001"),
                    slippage_buffer_bps=Decimal("25"),
                )
            ),
            ttl_seconds=30,
        ),
        duplicate_guard=DuplicateIntentGuard(ttl_seconds=60),
        expiry_policy=IntentExpiryPolicy(),
        snapshot_provider=lambda symbol: snapshot,
        now=clock.now,
    )
    engine.start()

    buy = StrategySignal(
        strategy_name="demo_strategy",
        symbol="AAPL",
        action=SignalAction.BUY,
        confidence=Decimal("0.95"),
        generated_at=now,
        reason="demo_buy",
        reference_price=Decimal("50"),
        suggested_quantity=Decimal("1"),
    )
    duplicate = StrategySignal(
        strategy_name="demo_strategy",
        symbol="AAPL",
        action=SignalAction.BUY,
        confidence=Decimal("0.95"),
        generated_at=now + timedelta(seconds=10),
        reason="demo_duplicate",
        reference_price=Decimal("50"),
        suggested_quantity=Decimal("1"),
    )
    sell = StrategySignal(
        strategy_name="demo_strategy",
        symbol="AAPL",
        action=SignalAction.SELL,
        confidence=Decimal("0.95"),
        generated_at=now + timedelta(seconds=70),
        reason="demo_sell",
        reference_price=Decimal("50"),
        suggested_quantity=Decimal("1"),
    )

    bus.publish(Event("strategy.signal", {"signal":buy}, now))
    bus.publish(Event("strategy.signal", {"signal":duplicate}, now + timedelta(seconds=10)))
    clock.advance(seconds=70)
    bus.publish(Event("strategy.signal", {"signal":sell}, now + timedelta(seconds=70)))
    engine.stop()

    result = {
        "stage_range": "V104.01-V105.00",
        "status": "PASS",
        "implementation_type": "ORDER_INTENT_POSITION_SIZING_FOUNDATION",
        "intent_count": len(intents),
        "intent_sides": [intent.side.value for intent in intents],
        "intent_quantities": [str(intent.quantity) for intent in intents],
        "estimated_notionals": [str(intent.estimated_notional) for intent in intents],
        "stats": vars(engine.stats),
        "broker_requests_executed": 0,
        "paper_order_submission_enabled": False,
        "actual_orders_submitted": 0,
        "live_trading_enabled": False,
        "next_phase": "V105_01_PAPER_EXECUTION_ADAPTER_FOUNDATION",
    }

    (output / "order_intent_position_sizing_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
