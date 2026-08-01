from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from runtime_engine import EventBus, ManualClock
from market_data_engine import (
    AlpacaMessageParser,
    Bar,
    ConnectionState,
    ConnectionStateMachine,
    ExponentialBackoff,
    FixtureMarketDataStream,
    FreshnessMonitor,
    FreshnessStatus,
    MarketDataRouter,
    MessageParseError,
    Quote,
    SequenceDecision,
    SequenceGuard,
    SubscriptionRegistry,
    Trade,
)


class MarketDataFoundationTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 8, 1, 16, 0, tzinfo=timezone.utc)
        self.parser = AlpacaMessageParser()

    def test_parse_quote(self):
        q = self.parser.parse_one({"T":"q","S":"aapl","t":"2026-08-01T16:00:00Z","bp":100,"bs":2,"ap":100.1,"as":3,"seq":1})
        self.assertIsInstance(q, Quote)
        self.assertEqual(q.symbol, "AAPL")
        self.assertEqual(q.midpoint, Decimal("100.05"))

    def test_parse_trade(self):
        t = self.parser.parse_one({"T":"t","S":"AAPL","t":"2026-08-01T16:00:00Z","p":"100.05","s":4,"x":"V","seq":2})
        self.assertIsInstance(t, Trade)
        self.assertEqual(t.size, 4)

    def test_parse_bar(self):
        b = self.parser.parse_one({"T":"b","S":"AAPL","t":"2026-08-01T16:00:00Z","o":100,"h":101,"l":99,"c":100.5,"v":1000,"n":12,"vw":100.4,"seq":3})
        self.assertIsInstance(b, Bar)
        self.assertEqual(b.volume, 1000)

    def test_ignore_control_messages(self):
        self.assertIsNone(self.parser.parse_one({"T":"success","msg":"authenticated"}))

    def test_reject_crossed_quote(self):
        with self.assertRaises(MessageParseError):
            self.parser.parse_one({"T":"q","S":"AAPL","t":"2026-08-01T16:00:00Z","bp":101,"bs":1,"ap":100,"as":1})

    def test_subscription_registry(self):
        registry = SubscriptionRegistry()
        registry.subscribe(quotes=["aapl"], trades=["msft"], bars=["spy"])
        self.assertTrue(registry.accepts("quote","AAPL"))
        self.assertEqual(registry.alpaca_subscribe_message()["quotes"], ["AAPL"])
        registry.unsubscribe(quotes=["AAPL"])
        self.assertFalse(registry.accepts("quote","AAPL"))

    def test_sequence_guard(self):
        guard = SequenceGuard()
        q1 = self.parser.parse_one({"T":"q","S":"AAPL","t":"2026-08-01T16:00:00Z","bp":100,"bs":1,"ap":101,"as":1,"seq":5})
        q2 = self.parser.parse_one({"T":"q","S":"AAPL","t":"2026-08-01T16:00:01Z","bp":100,"bs":1,"ap":101,"as":1,"seq":5})
        q3 = self.parser.parse_one({"T":"q","S":"AAPL","t":"2026-08-01T16:00:02Z","bp":100,"bs":1,"ap":101,"as":1,"seq":4})
        self.assertEqual(guard.check(q1), SequenceDecision.ACCEPT)
        self.assertEqual(guard.check(q2), SequenceDecision.DUPLICATE)
        self.assertEqual(guard.check(q3), SequenceDecision.OUT_OF_ORDER)

    def test_freshness_monitor(self):
        monitor = FreshnessMonitor(10, future_tolerance_seconds=1)
        self.assertEqual(monitor.status(message_time=self.now, now=self.now), FreshnessStatus.FRESH)
        self.assertEqual(monitor.status(message_time=self.now-timedelta(seconds=11), now=self.now), FreshnessStatus.STALE)
        self.assertEqual(monitor.status(message_time=self.now+timedelta(seconds=2), now=self.now), FreshnessStatus.FUTURE)

    def test_connection_state_machine(self):
        sm = ConnectionStateMachine()
        for target in [ConnectionState.CONNECTING, ConnectionState.AUTHENTICATING,
                       ConnectionState.SUBSCRIBING, ConnectionState.STREAMING,
                       ConnectionState.STOPPED]:
            sm.transition(target)
        self.assertEqual(sm.state, ConnectionState.STOPPED)

    def test_invalid_connection_transition(self):
        sm = ConnectionStateMachine()
        with self.assertRaises(RuntimeError):
            sm.transition(ConnectionState.STREAMING)

    def test_backoff_caps_and_resets(self):
        backoff = ExponentialBackoff(initial_seconds=1, multiplier=2, maximum_seconds=4)
        self.assertEqual([backoff.next_delay() for _ in range(4)], [1,2,4,4])
        backoff.reset()
        self.assertEqual(backoff.next_delay(), 1)

    def test_router_publishes_only_valid_messages(self):
        clock = ManualClock(self.now)
        bus = EventBus()
        seen = []
        bus.subscribe("market_data.quote", lambda event: seen.append(event.payload["message"]))
        registry = SubscriptionRegistry()
        registry.subscribe(quotes=["AAPL"])
        router = MarketDataRouter(
            event_bus=bus,
            subscriptions=registry,
            sequence_guard=SequenceGuard(),
            freshness_monitor=FreshnessMonitor(10),
            now=clock.now,
        )
        fresh = self.parser.parse_one({"T":"q","S":"AAPL","t":"2026-08-01T16:00:00Z","bp":100,"bs":1,"ap":101,"as":1,"seq":1})
        duplicate = self.parser.parse_one({"T":"q","S":"AAPL","t":"2026-08-01T16:00:01Z","bp":100,"bs":1,"ap":101,"as":1,"seq":1})
        self.assertTrue(router.route(fresh))
        self.assertFalse(router.route(duplicate))
        self.assertEqual(len(seen), 1)
        self.assertEqual(router.stats.duplicates, 1)

    def test_fixture_stream_end_to_end(self):
        clock = ManualClock(self.now)
        bus = EventBus()
        registry = SubscriptionRegistry()
        registry.subscribe(quotes=["AAPL"], trades=["AAPL"], bars=["AAPL"])
        router = MarketDataRouter(
            event_bus=bus,
            subscriptions=registry,
            sequence_guard=SequenceGuard(),
            freshness_monitor=FreshnessMonitor(10),
            now=clock.now,
        )
        frames = [[
            {"T":"q","S":"AAPL","t":"2026-08-01T16:00:00Z","bp":100,"bs":1,"ap":101,"as":1,"seq":1},
            {"T":"t","S":"AAPL","t":"2026-08-01T16:00:00Z","p":100.5,"s":1,"seq":1},
            {"T":"b","S":"AAPL","t":"2026-08-01T16:00:00Z","o":100,"h":101,"l":99,"c":100.5,"v":10,"seq":1},
        ]]
        result = FixtureMarketDataStream(frames=frames, parser=self.parser, router=router).run()
        self.assertEqual(result["published_count"], 3)
        self.assertEqual(len(bus.history()), 3)


if __name__ == "__main__":
    unittest.main()
