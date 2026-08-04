from __future__ import annotations
import unittest
from ai_signal_intelligence.engine import analyze
from ai_signal_intelligence.indicators import ema, rsi
from ai_signal_intelligence.models import Bar
from ai_signal_intelligence.patterns import detect


def bars(up: bool = True):
    result = []
    price = 100.0
    for i in range(30):
        next_price = price + (1.0 if up else -1.0)
        result.append({
            "open": price,
            "high": max(price, next_price) + 0.4,
            "low": min(price, next_price) - 0.4,
            "close": next_price,
            "volume": 1000 + i * 25,
        })
        price = next_price
    return result


class Tests(unittest.TestCase):
    def test_ema(self):
        self.assertGreater(ema([1, 2, 3], 2), 2)

    def test_rsi_up(self):
        self.assertGreater(rsi(list(range(1, 20))), 90)

    def test_bull_signal(self):
        result = analyze({"symbol": "AAPL", "bars": bars(True), "market_trend": 0.7, "news_score": 0.5})
        self.assertIn(result.action, {"BUY", "HOLD"})
        self.assertFalse(result.order_submission_allowed)

    def test_bear_signal(self):
        result = analyze({"symbol": "AAPL", "bars": bars(False), "market_trend": -0.7, "news_score": -0.5})
        self.assertIn(result.action, {"SELL", "HOLD"})

    def test_invalid_ohlc(self):
        value = bars()
        value[-1]["high"] = value[-1]["low"] - 1
        with self.assertRaises(ValueError):
            analyze({"symbol": "AAPL", "bars": value})

    def test_engulfing(self):
        value = [
            Bar(10, 11, 8, 9, 100),
            Bar(8.5, 11.5, 8, 11, 120),
        ]
        self.assertIn("BULLISH_ENGULFING", detect(value))

    def test_deterministic(self):
        payload = {"symbol": "AAPL", "bars": bars(True), "market_trend": 0.2}
        self.assertEqual(analyze(payload).to_dict(), analyze(payload).to_dict())

    def test_zero_orders(self):
        result = analyze({"symbol": "AAPL", "bars": bars(True)})
        self.assertEqual(result.actual_paper_orders_submitted, 0)
        self.assertEqual(result.actual_live_orders_submitted, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
