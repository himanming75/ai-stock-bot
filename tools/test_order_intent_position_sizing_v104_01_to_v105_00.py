from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from runtime_engine import Event, EventBus, ManualClock
from strategy_engine import MarketSnapshot, SignalAction, StrategySignal
from execution_engine import (
    DuplicateIntentGuard,
    IntentExpiryPolicy,
    OrderIntentEngine,
    OrderIntentFactory,
    OrderSide,
    PositionSizer,
    PositionSizingConfig,
)


class OrderIntentPositionSizingTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 1, 16, 0, tzinfo=timezone.utc)
        self.snapshot = MarketSnapshot(
            symbol="AAPL",
            timestamp=self.now,
            last_price=Decimal("50"),
            bid_price=Decimal("49.99"),
            ask_price=Decimal("50.01"),
            recent_closes=(Decimal("49"), Decimal("50")),
            position_quantity=Decimal("2"),
            cash_available=Decimal("1000"),
        )

    def signal(self, action=SignalAction.BUY, price="50", generated_at=None):
        return StrategySignal(
            strategy_name="test_strategy",
            symbol="AAPL",
            action=action,
            confidence=Decimal("0.9"),
            generated_at=generated_at or self.now,
            reason="test",
            reference_price=Decimal(price),
            suggested_quantity=Decimal("1") if action != SignalAction.HOLD else Decimal("0"),
        )

    def test_config_validation(self):
        PositionSizingConfig().validate()
        with self.assertRaises(ValueError):
            PositionSizingConfig(max_quantity=Decimal("0")).validate()

    def test_buy_sizing_uses_cash_fraction_and_caps_quantity(self):
        sizer = PositionSizer(PositionSizingConfig(cash_fraction=Decimal("0.10")))
        result = sizer.size(self.signal(), self.snapshot)
        self.assertTrue(result.accepted)
        self.assertLessEqual(result.quantity, Decimal("1"))
        self.assertLessEqual(result.estimated_notional, Decimal("100"))

    def test_sell_sizing_uses_position(self):
        sizer = PositionSizer(PositionSizingConfig(sell_fraction=Decimal("0.50")))
        result = sizer.size(self.signal(SignalAction.SELL), self.snapshot)
        self.assertTrue(result.accepted)
        self.assertEqual(result.quantity, Decimal("1.000"))

    def test_fractional_rounding(self):
        snapshot = MarketSnapshot(**{**self.snapshot.__dict__, "cash_available":Decimal("10")})
        sizer = PositionSizer(PositionSizingConfig(cash_fraction=Decimal("1"), fractional_step=Decimal("0.01")))
        result = sizer.size(self.signal(price="33"), snapshot)
        self.assertEqual(result.quantity, Decimal("0.30"))

    def test_slippage_buffer_applied(self):
        sizer = PositionSizer(PositionSizingConfig(slippage_buffer_bps=Decimal("100")))
        buy = sizer.size(self.signal(SignalAction.BUY), self.snapshot)
        sell = sizer.size(self.signal(SignalAction.SELL), self.snapshot)
        self.assertEqual(buy.effective_price, Decimal("50.50"))
        self.assertEqual(sell.effective_price, Decimal("49.50"))

    def test_hold_rejected(self):
        sizer = PositionSizer(PositionSizingConfig())
        result = sizer.size(self.signal(SignalAction.HOLD), self.snapshot)
        self.assertFalse(result.accepted)

    def test_factory_creates_buy_intent(self):
        factory = OrderIntentFactory(position_sizer=PositionSizer(PositionSizingConfig()), ttl_seconds=30)
        intent = factory.create(self.signal(), self.snapshot)
        self.assertEqual(intent.side, OrderSide.BUY)
        self.assertEqual(intent.expires_at, self.now + timedelta(seconds=30))

    def test_factory_creates_sell_intent(self):
        factory = OrderIntentFactory(position_sizer=PositionSizer(PositionSizingConfig()), ttl_seconds=30)
        intent = factory.create(self.signal(SignalAction.SELL), self.snapshot)
        self.assertEqual(intent.side, OrderSide.SELL)

    def test_duplicate_intent_guard(self):
        factory = OrderIntentFactory(position_sizer=PositionSizer(PositionSizingConfig()), ttl_seconds=30)
        guard = DuplicateIntentGuard(ttl_seconds=60)
        intent = factory.create(self.signal(), self.snapshot)
        self.assertFalse(guard.is_duplicate(intent))
        later_signal = self.signal(generated_at=self.now + timedelta(seconds=10))
        later_intent = factory.create(later_signal, self.snapshot)
        self.assertTrue(guard.is_duplicate(later_intent))

    def test_expiry_policy(self):
        factory = OrderIntentFactory(position_sizer=PositionSizer(PositionSizingConfig()), ttl_seconds=30)
        intent = factory.create(self.signal(), self.snapshot)
        policy = IntentExpiryPolicy()
        self.assertFalse(policy.is_expired(intent, self.now + timedelta(seconds=29)))
        self.assertTrue(policy.is_expired(intent, self.now + timedelta(seconds=30)))

    def test_engine_converts_signal_event_to_intent_event(self):
        bus = EventBus()
        clock = ManualClock(self.now)
        seen = []
        bus.subscribe("order.intent", lambda event: seen.append(event.payload["intent"]))
        engine = OrderIntentEngine(
            event_bus=bus,
            intent_factory=OrderIntentFactory(position_sizer=PositionSizer(PositionSizingConfig()), ttl_seconds=30),
            duplicate_guard=DuplicateIntentGuard(ttl_seconds=60),
            expiry_policy=IntentExpiryPolicy(),
            snapshot_provider=lambda symbol: self.snapshot,
            now=clock.now,
        )
        engine.start()
        bus.publish(Event("strategy.signal", {"signal":self.signal()}, self.now))
        self.assertEqual(len(seen), 1)
        self.assertEqual(engine.stats.published, 1)
        engine.stop()

    def test_engine_rejects_duplicate(self):
        bus = EventBus()
        clock = ManualClock(self.now)
        engine = OrderIntentEngine(
            event_bus=bus,
            intent_factory=OrderIntentFactory(position_sizer=PositionSizer(PositionSizingConfig()), ttl_seconds=30),
            duplicate_guard=DuplicateIntentGuard(ttl_seconds=60),
            expiry_policy=IntentExpiryPolicy(),
            snapshot_provider=lambda symbol: self.snapshot,
            now=clock.now,
        )
        self.assertIsNotNone(engine.process(self.signal()))
        self.assertIsNone(engine.process(self.signal(generated_at=self.now+timedelta(seconds=10))))
        self.assertEqual(engine.stats.rejected_duplicate, 1)

    def test_engine_rejects_expired_intent(self):
        bus = EventBus()
        clock = ManualClock(self.now + timedelta(seconds=31))
        engine = OrderIntentEngine(
            event_bus=bus,
            intent_factory=OrderIntentFactory(position_sizer=PositionSizer(PositionSizingConfig()), ttl_seconds=30),
            duplicate_guard=DuplicateIntentGuard(ttl_seconds=60),
            expiry_policy=IntentExpiryPolicy(),
            snapshot_provider=lambda symbol: self.snapshot,
            now=clock.now,
        )
        self.assertIsNone(engine.process(self.signal()))
        self.assertEqual(engine.stats.rejected_expired, 1)

    def test_engine_rejects_insufficient_cash(self):
        poor_snapshot = MarketSnapshot(**{**self.snapshot.__dict__, "cash_available":Decimal("0")})
        engine = OrderIntentEngine(
            event_bus=EventBus(),
            intent_factory=OrderIntentFactory(position_sizer=PositionSizer(PositionSizingConfig()), ttl_seconds=30),
            duplicate_guard=DuplicateIntentGuard(),
            expiry_policy=IntentExpiryPolicy(),
            snapshot_provider=lambda symbol: poor_snapshot,
            now=lambda: self.now,
        )
        self.assertIsNone(engine.process(self.signal()))
        self.assertEqual(engine.stats.rejected_sizing, 1)


if __name__ == "__main__":
    unittest.main()
