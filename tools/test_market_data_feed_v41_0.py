from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.market_data_feed_v41_0 import (
    MarketDataFeed,
    QuoteInput,
    TradeInput,
    canonical_hash,
)


NOW = "2026-07-29T17:00:00+00:00"


class MarketDataFeedV410Tests(unittest.TestCase):
    def feed(self, **kwargs) -> MarketDataFeed:
        return MarketDataFeed(reference_time=NOW, max_age_seconds=60, **kwargs)

    def test_quote_accepted(self) -> None:
        feed = self.feed()
        event = feed.accept_quote(
            QuoteInput("AAPL", "199.9", "200.1", "100", "120", NOW)
        )
        self.assertEqual(event.event_type, "quote")
        self.assertEqual(event.symbol, "AAPL")

    def test_trade_accepted(self) -> None:
        feed = self.feed()
        event = feed.accept_trade(TradeInput("aapl", "200", "10", NOW))
        self.assertEqual(event.payload["price"], "200")
        self.assertEqual(event.symbol, "AAPL")

    def test_crossed_quote_rejected(self) -> None:
        feed = self.feed()
        with self.assertRaises(ValueError):
            feed.accept_quote(QuoteInput("AAPL", "201", "200", "1", "1", NOW))

    def test_zero_trade_size_rejected(self) -> None:
        feed = self.feed()
        with self.assertRaises(ValueError):
            feed.accept_trade(TradeInput("AAPL", "200", "0", NOW))

    def test_stale_quote_rejected(self) -> None:
        feed = self.feed()
        with self.assertRaises(TimeoutError):
            feed.accept_quote(
                QuoteInput("AAPL", "199", "200", "1", "1", "2026-07-29T16:58:00+00:00")
            )

    def test_midpoint_and_spread(self) -> None:
        feed = self.feed()
        feed.accept_quote(QuoteInput("AAPL", "199.9", "200.1", "1", "1", NOW))
        receipt = feed.receipt()
        self.assertEqual(receipt.midpoint, "200")
        self.assertEqual(receipt.spread, "0.2")

    def test_replay_mixed_records(self) -> None:
        feed = self.feed()
        receipt = feed.replay(
            [
                {"type": "quote", "symbol": "AAPL", "bid": "199", "ask": "201",
                 "bid_size": "1", "ask_size": "1", "timestamp": NOW},
                {"type": "trade", "symbol": "AAPL", "price": "200", "size": "2",
                 "timestamp": NOW},
            ]
        )
        self.assertEqual(receipt.accepted_event_count, 2)
        self.assertEqual(receipt.rejected_event_count, 0)
        self.assertEqual(receipt.status, "accepted")

    def test_replay_records_rejection(self) -> None:
        feed = self.feed()
        receipt = feed.replay([{"type": "bad"}])
        self.assertEqual(receipt.accepted_event_count, 0)
        self.assertEqual(receipt.rejected_event_count, 1)
        self.assertEqual(receipt.status, "rejected_invalid")

    def test_live_gate_rejects_without_enable(self) -> None:
        feed = self.feed(mode="live")
        with self.assertRaises(PermissionError):
            feed.accept_trade(TradeInput("AAPL", "200", "1", NOW))

    def test_live_transport_not_implemented(self) -> None:
        feed = self.feed(mode="live", enable_live=True)
        with self.assertRaises(NotImplementedError):
            feed.accept_trade(TradeInput("AAPL", "200", "1", NOW))

    def test_event_hash_present(self) -> None:
        feed = self.feed()
        event = feed.accept_trade(TradeInput("AAPL", "200", "1", NOW))
        self.assertEqual(len(event.event_sha256), 64)

    def test_snapshot_hash_present(self) -> None:
        feed = self.feed()
        feed.accept_trade(TradeInput("AAPL", "200", "1", NOW))
        receipt = feed.receipt()
        self.assertEqual(len(receipt.snapshot_sha256), 64)

    def test_hash_is_deterministic(self) -> None:
        payload = {"b": 2, "a": 1}
        self.assertEqual(canonical_hash(payload), canonical_hash({"a": 1, "b": 2}))

    def test_export_contains_no_network_usage(self) -> None:
        feed = self.feed()
        feed.accept_trade(TradeInput("AAPL", "200", "1", NOW))
        receipt = feed.receipt()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "result.json"
            feed.export(path, receipt)
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertFalse(payload["network_used"])
        self.assertFalse(payload["receipt"]["network_used"])


if __name__ == "__main__":
    unittest.main()
