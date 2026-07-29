from __future__ import annotations

import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from tools.strategy_engine_v42_0 import (
    Decision,
    StrategyConfig,
    StrategyEngine,
    Trend,
    Momentum,
    canonical_hash,
    classify_momentum,
    classify_trend,
    parse_prices,
    sma,
)


class StrategyEngineV420Tests(unittest.TestCase):
    def engine(self, **kwargs) -> StrategyEngine:
        return StrategyEngine(StrategyConfig(), **kwargs)

    def test_sma(self) -> None:
        prices = parse_prices([1, 2, 3, 4, 5])
        self.assertEqual(sma(prices, 5), Decimal("3"))

    def test_sma_insufficient(self) -> None:
        self.assertIsNone(sma(parse_prices([1, 2]), 3))

    def test_positive_momentum(self) -> None:
        self.assertEqual(
            classify_momentum(parse_prices([1, 2, 3, 4]), 2),
            Momentum.POSITIVE,
        )

    def test_negative_momentum(self) -> None:
        self.assertEqual(
            classify_momentum(parse_prices([4, 3, 2, 1]), 2),
            Momentum.NEGATIVE,
        )

    def test_neutral_momentum(self) -> None:
        self.assertEqual(
            classify_momentum(parse_prices([1, 1, 1, 1]), 2),
            Momentum.NEUTRAL,
        )

    def test_uptrend(self) -> None:
        self.assertEqual(
            classify_trend(Decimal("101"), Decimal("100")),
            Trend.UPTREND,
        )

    def test_downtrend(self) -> None:
        self.assertEqual(
            classify_trend(Decimal("99"), Decimal("100")),
            Trend.DOWNTREND,
        )

    def test_sideways(self) -> None:
        self.assertEqual(
            classify_trend(Decimal("100.05"), Decimal("100")),
            Trend.SIDEWAYS,
        )

    def test_buy_decision(self) -> None:
        result = self.engine().evaluate("AAPL", list(range(100, 125)))
        self.assertEqual(result.decision, Decision.BUY.value)
        self.assertEqual(result.trend, Trend.UPTREND.value)

    def test_sell_decision(self) -> None:
        result = self.engine().evaluate("AAPL", list(range(125, 100, -1)))
        self.assertEqual(result.decision, Decision.SELL.value)
        self.assertEqual(result.trend, Trend.DOWNTREND.value)

    def test_hold_decision_sideways(self) -> None:
        result = self.engine().evaluate("AAPL", [100] * 25)
        self.assertEqual(result.decision, Decision.HOLD.value)

    def test_insufficient_data_forces_hold(self) -> None:
        result = self.engine().evaluate("AAPL", [100, 101, 102])
        self.assertEqual(result.decision, Decision.HOLD.value)
        self.assertLessEqual(result.confidence, 50)

    def test_invalid_empty_prices(self) -> None:
        with self.assertRaises(ValueError):
            self.engine().evaluate("AAPL", [])

    def test_invalid_zero_price(self) -> None:
        with self.assertRaises(ValueError):
            self.engine().evaluate("AAPL", [100, 0])

    def test_invalid_symbol(self) -> None:
        with self.assertRaises(ValueError):
            self.engine().evaluate(" ", [100] * 25)

    def test_hash_present(self) -> None:
        result = self.engine().evaluate("AAPL", [100] * 25)
        self.assertEqual(len(result.decision_sha256), 64)

    def test_hash_deterministic(self) -> None:
        self.assertEqual(
            canonical_hash({"b": 2, "a": 1}),
            canonical_hash({"a": 1, "b": 2}),
        )

    def test_network_false(self) -> None:
        result = self.engine().evaluate("AAPL", [100] * 25)
        self.assertFalse(result.network_used)

    def test_live_gate(self) -> None:
        with self.assertRaises(PermissionError):
            self.engine(mode="live").evaluate("AAPL", [100] * 25)

    def test_live_transport_not_implemented(self) -> None:
        with self.assertRaises(NotImplementedError):
            self.engine(mode="live", enable_live=True).evaluate("AAPL", [100] * 25)

    def test_export(self) -> None:
        result = self.engine().evaluate("AAPL", [100] * 25)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "result.json"
            StrategyEngine.export(path, result)
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertFalse(payload["network_used"])
        self.assertEqual(payload["result"]["decision"], "HOLD")


if __name__ == "__main__":
    unittest.main()
