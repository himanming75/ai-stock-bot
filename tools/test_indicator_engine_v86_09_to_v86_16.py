from __future__ import annotations

import unittest

from indicator_engine.calculations import (
    atr,
    bollinger_bands,
    ema,
    macd,
    rsi,
    sma,
    vwap,
)
from indicator_engine.engine import evaluate_indicators
from indicator_engine.models import Bar


def sample_bars(count=220):
    bars = []
    close = 100.0
    for index in range(count):
        close += 0.25 + ((index % 5) - 2) * 0.05
        bars.append(Bar(
            timestamp=f"2026-01-{(index % 28) + 1:02d}T16:00:00Z",
            open=close - 0.2,
            high=close + 0.5,
            low=close - 0.5,
            close=close,
            volume=1000 + index * 10,
        ))
    return bars


class IndicatorEngineTests(unittest.TestCase):
    def test_sma(self):
        self.assertEqual(sma([1, 2, 3, 4, 5], 3), 4.0)

    def test_ema(self):
        value = ema([1, 2, 3, 4, 5], 3)
        self.assertIsNotNone(value)
        self.assertGreater(value, 3)

    def test_rsi_uptrend(self):
        value = rsi(list(range(1, 20)), 14)
        self.assertEqual(value, 100.0)

    def test_macd_available(self):
        result = macd(list(range(1, 40)))
        self.assertIsNotNone(result["macd"])
        self.assertIsNotNone(result["signal"])

    def test_atr(self):
        value = atr(sample_bars(20), 14)
        self.assertIsNotNone(value)
        self.assertGreater(value, 0)

    def test_bollinger(self):
        result = bollinger_bands(list(range(1, 30)), 20)
        self.assertGreater(result["upper"], result["middle"])
        self.assertLess(result["lower"], result["middle"])

    def test_vwap(self):
        value = vwap(sample_bars(5))
        self.assertIsNotNone(value)
        self.assertGreater(value, 0)

    def test_engine_outputs_strategy_signals(self):
        result = evaluate_indicators("AAPL", sample_bars())
        self.assertEqual(result["symbol"], "AAPL")
        self.assertGreaterEqual(len(result["strategy_signals"]), 4)
        self.assertIsNotNone(result["ema_200"])


if __name__ == "__main__":
    unittest.main()
