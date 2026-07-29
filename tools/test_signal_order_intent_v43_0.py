from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.signal_order_intent_v43_0 import (
    IntentConfig,
    SignalInput,
    SignalOrderIntentEngine,
    canonical_hash,
    load_strategy_result,
)


NOW = "2026-07-29T17:00:00+00:00"
SHA = "a" * 64


class SignalOrderIntentV430Tests(unittest.TestCase):
    def engine(self, **kwargs) -> SignalOrderIntentEngine:
        return SignalOrderIntentEngine(
            IntentConfig(),
            reference_time=NOW,
            **kwargs,
        )

    def signal(self, **overrides) -> SignalInput:
        values = {
            "symbol": "AAPL",
            "decision": "BUY",
            "confidence": 90,
            "latest_price": "200",
            "generated_at": NOW,
            "source_sha256": SHA,
        }
        values.update(overrides)
        return SignalInput(**values)

    def test_buy_intent_accepted(self) -> None:
        result = self.engine().create_intent(self.signal())
        self.assertEqual(result.status, "ACCEPTED")
        self.assertEqual(result.side, "buy")
        self.assertEqual(result.quantity, "50")

    def test_sell_intent_accepted(self) -> None:
        result = self.engine().create_intent(
            self.signal(decision="SELL", source_sha256="b" * 64),
            quantity="5",
        )
        self.assertEqual(result.status, "ACCEPTED")
        self.assertEqual(result.side, "sell")
        self.assertEqual(result.quantity, "5")

    def test_hold_rejected(self) -> None:
        result = self.engine().create_intent(
            self.signal(decision="HOLD", source_sha256="c" * 64)
        )
        self.assertEqual(result.status, "REJECTED")
        self.assertIn("HOLD signals", result.rejection_reasons[0])

    def test_low_confidence_rejected(self) -> None:
        result = self.engine().create_intent(
            self.signal(confidence=40, source_sha256="d" * 64)
        )
        self.assertEqual(result.status, "REJECTED")

    def test_stale_signal_rejected(self) -> None:
        result = self.engine().create_intent(
            self.signal(
                generated_at="2026-07-29T16:50:00+00:00",
                source_sha256="e" * 64,
            )
        )
        self.assertEqual(result.status, "REJECTED")
        self.assertTrue(any("stale" in x.lower() for x in result.rejection_reasons))

    def test_future_signal_rejected(self) -> None:
        result = self.engine().create_intent(
            self.signal(
                generated_at="2026-07-29T17:01:00+00:00",
                source_sha256="f" * 64,
            )
        )
        self.assertEqual(result.status, "REJECTED")

    def test_duplicate_rejected(self) -> None:
        engine = self.engine()
        first = engine.create_intent(self.signal())
        second = engine.create_intent(self.signal())
        self.assertEqual(first.status, "ACCEPTED")
        self.assertEqual(second.status, "REJECTED")
        self.assertTrue(any("Duplicate" in x for x in second.rejection_reasons))

    def test_limit_order_requires_price(self) -> None:
        result = self.engine().create_intent(
            self.signal(source_sha256="1" * 64),
            order_type="limit",
        )
        self.assertEqual(result.status, "REJECTED")

    def test_limit_order_accepted(self) -> None:
        result = self.engine().create_intent(
            self.signal(source_sha256="2" * 64),
            order_type="limit",
            limit_price="199.5",
        )
        self.assertEqual(result.status, "ACCEPTED")
        self.assertEqual(result.limit_price, "199.5")

    def test_market_order_rejects_limit_price(self) -> None:
        result = self.engine().create_intent(
            self.signal(source_sha256="3" * 64),
            order_type="market",
            limit_price="199",
        )
        self.assertEqual(result.status, "REJECTED")

    def test_explicit_quantity(self) -> None:
        result = self.engine().create_intent(
            self.signal(source_sha256="4" * 64),
            quantity="7",
        )
        self.assertEqual(result.quantity, "7")

    def test_quantity_capped(self) -> None:
        config = IntentConfig(max_quantity=10)
        engine = SignalOrderIntentEngine(config, reference_time=NOW)
        result = engine.create_intent(
            self.signal(source_sha256="5" * 64),
            available_cash="1000000",
        )
        self.assertEqual(result.quantity, "10")

    def test_fractional_quantity(self) -> None:
        config = IntentConfig(allow_fractional=True)
        engine = SignalOrderIntentEngine(config, reference_time=NOW)
        result = engine.create_intent(
            self.signal(source_sha256="6" * 64, latest_price="300"),
            available_cash="1000",
        )
        self.assertEqual(result.quantity, "0.3333333333333333333333333333")

    def test_invalid_hash_rejected(self) -> None:
        result = self.engine().create_intent(
            self.signal(source_sha256="not-a-hash")
        )
        self.assertEqual(result.status, "REJECTED")

    def test_client_order_id_deterministic(self) -> None:
        first = self.engine().create_intent(self.signal())
        second = self.engine().create_intent(self.signal())
        self.assertEqual(first.client_order_id, second.client_order_id)

    def test_intent_hash_present(self) -> None:
        result = self.engine().create_intent(self.signal())
        self.assertEqual(len(result.intent_sha256), 64)

    def test_canonical_hash_deterministic(self) -> None:
        self.assertEqual(
            canonical_hash({"b": 2, "a": 1}),
            canonical_hash({"a": 1, "b": 2}),
        )

    def test_network_false(self) -> None:
        result = self.engine().create_intent(self.signal())
        self.assertFalse(result.network_used)

    def test_live_gate(self) -> None:
        with self.assertRaises(PermissionError):
            self.engine(mode="live").create_intent(self.signal())

    def test_live_transport_not_implemented(self) -> None:
        with self.assertRaises(NotImplementedError):
            self.engine(mode="live", enable_live=True).create_intent(self.signal())

    def test_export(self) -> None:
        result = self.engine().create_intent(self.signal())
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "intent.json"
            SignalOrderIntentEngine.export(path, result)
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertFalse(payload["network_used"])
        self.assertEqual(payload["intent"]["status"], "ACCEPTED")

    def test_load_v42_result(self) -> None:
        payload = {
            "result": {
                "symbol": "AAPL",
                "decision": "BUY",
                "confidence": 90,
                "latest_price": "200",
                "decision_sha256": SHA,
                "version": "42.0",
                "generated_at": NOW,
            }
        }
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "v42.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            loaded = load_strategy_result(path)
        self.assertEqual(loaded.symbol, "AAPL")
        self.assertEqual(loaded.decision, "BUY")


if __name__ == "__main__":
    unittest.main()
