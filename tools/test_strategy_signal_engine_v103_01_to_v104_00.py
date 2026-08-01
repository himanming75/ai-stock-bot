from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from runtime_engine import EventBus
from strategy_engine import (
    ConfidenceFilter,
    CooldownFilter,
    DuplicateSignalGuard,
    MarketSnapshot,
    MovingAverageCrossStrategy,
    RiskPreFilter,
    SignalAction,
    SignalEngine,
    StrategySignal,
)


class StrategySignalEngineTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 1, 16, 0, tzinfo=timezone.utc)

    def snapshot(self, closes, **overrides):
        values = {
            "symbol": "AAPL",
            "timestamp": self.now,
            "last_price": Decimal("50"),
            "bid_price": Decimal("49.99"),
            "ask_price": Decimal("50.01"),
            "recent_closes": tuple(Decimal(str(x)) for x in closes),
            "position_quantity": Decimal("2"),
            "cash_available": Decimal("1000"),
        }
        values.update(overrides)
        return MarketSnapshot(**values)

    def test_snapshot_validation(self):
        self.snapshot([1,2,3]).validate()
        with self.assertRaises(ValueError):
            self.snapshot([1], symbol="aapl").validate()

    def test_signal_validation(self):
        signal = StrategySignal(
            strategy_name="x",
            symbol="AAPL",
            action=SignalAction.BUY,
            confidence=Decimal("0.8"),
            generated_at=self.now,
            reason="test",
            reference_price=Decimal("10"),
            suggested_quantity=Decimal("1"),
        )
        signal.validate()

    def test_strategy_hold_for_insufficient_history(self):
        strategy = MovingAverageCrossStrategy(short_window=2, long_window=4)
        signal = strategy.evaluate(self.snapshot([1,2,3]))
        self.assertEqual(signal.action, SignalAction.HOLD)

    def test_strategy_buy(self):
        strategy = MovingAverageCrossStrategy(short_window=2, long_window=4)
        signal = strategy.evaluate(self.snapshot([40,40,60,60]))
        self.assertEqual(signal.action, SignalAction.BUY)
        self.assertGreater(signal.confidence, Decimal("0"))

    def test_strategy_sell(self):
        strategy = MovingAverageCrossStrategy(short_window=2, long_window=4)
        signal = strategy.evaluate(self.snapshot([60,60,40,40]))
        self.assertEqual(signal.action, SignalAction.SELL)

    def test_confidence_filter(self):
        filter_ = ConfidenceFilter(Decimal("0.5"))
        signal = MovingAverageCrossStrategy(short_window=2, long_window=4).evaluate(self.snapshot([40,40,60,60]))
        self.assertTrue(filter_.check(signal).accepted)

    def test_duplicate_guard(self):
        guard = DuplicateSignalGuard(ttl_seconds=60)
        signal = MovingAverageCrossStrategy(short_window=2, long_window=4).evaluate(self.snapshot([40,40,60,60]))
        self.assertFalse(guard.is_duplicate(signal))
        same = StrategySignal(**{**signal.__dict__, "signal_id":"other", "generated_at":self.now+timedelta(seconds=30)})
        self.assertTrue(guard.is_duplicate(same))

    def test_cooldown_filter(self):
        filter_ = CooldownFilter(cooldown_seconds=60)
        signal = MovingAverageCrossStrategy(short_window=2, long_window=4).evaluate(self.snapshot([40,40,60,60]))
        self.assertTrue(filter_.check(signal).accepted)
        later = StrategySignal(**{**signal.__dict__, "signal_id":"later", "generated_at":self.now+timedelta(seconds=30)})
        self.assertFalse(filter_.check(later).accepted)

    def test_risk_filter_notional(self):
        risk = RiskPreFilter(max_quantity=Decimal("1"), max_notional=Decimal("20"))
        signal = MovingAverageCrossStrategy(short_window=2, long_window=4).evaluate(self.snapshot([40,40,60,60]))
        self.assertFalse(risk.check(signal, self.snapshot([40,40,60,60])).accepted)

    def test_risk_filter_sell_position(self):
        risk = RiskPreFilter()
        signal = MovingAverageCrossStrategy(short_window=2, long_window=4).evaluate(self.snapshot([60,60,40,40]))
        snapshot = self.snapshot([60,60,40,40], position_quantity=Decimal("0"))
        self.assertFalse(risk.check(signal, snapshot).accepted)

    def test_engine_publishes_accepted_signal(self):
        bus = EventBus()
        seen = []
        bus.subscribe("strategy.signal", lambda event: seen.append(event.payload["signal"]))
        engine = SignalEngine(
            event_bus=bus,
            strategies=[MovingAverageCrossStrategy(short_window=2, long_window=4)],
            confidence_filter=ConfidenceFilter(Decimal("0.1")),
            cooldown_filter=CooldownFilter(cooldown_seconds=60),
            duplicate_guard=DuplicateSignalGuard(ttl_seconds=60),
            risk_filter=RiskPreFilter(max_notional=Decimal("100")),
        )
        accepted = engine.evaluate(self.snapshot([40,40,60,60]))
        self.assertEqual(len(accepted), 1)
        self.assertEqual(len(seen), 1)
        self.assertEqual(engine.stats.accepted, 1)

    def test_engine_rejects_duplicate(self):
        bus = EventBus()
        engine = SignalEngine(
            event_bus=bus,
            strategies=[MovingAverageCrossStrategy(short_window=2, long_window=4)],
            confidence_filter=ConfidenceFilter(Decimal("0.1")),
            cooldown_filter=CooldownFilter(cooldown_seconds=60),
            duplicate_guard=DuplicateSignalGuard(ttl_seconds=60),
            risk_filter=RiskPreFilter(max_notional=Decimal("100")),
        )
        self.assertEqual(len(engine.evaluate(self.snapshot([40,40,60,60]))), 1)
        later_snapshot = self.snapshot([40,40,60,60], timestamp=self.now+timedelta(seconds=30))
        self.assertEqual(len(engine.evaluate(later_snapshot)), 0)
        self.assertEqual(engine.stats.rejected_duplicate, 1)

    def test_engine_rejects_low_confidence(self):
        engine = SignalEngine(
            event_bus=EventBus(),
            strategies=[MovingAverageCrossStrategy(short_window=2, long_window=4)],
            confidence_filter=ConfidenceFilter(Decimal("0.9")),
            cooldown_filter=CooldownFilter(),
            duplicate_guard=DuplicateSignalGuard(),
            risk_filter=RiskPreFilter(max_notional=Decimal("100")),
        )
        accepted = engine.evaluate(self.snapshot([49,49,50,50]))
        self.assertEqual(accepted, [])
        self.assertEqual(engine.stats.rejected_confidence, 1)


if __name__ == "__main__":
    unittest.main()
