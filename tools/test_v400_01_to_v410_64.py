from __future__ import annotations
import unittest
from offline_ai_decision_engine.engine import decide
from offline_ai_decision_engine.regime import classify
from offline_ai_decision_engine.models import MarketInput


BULL = {
    "symbol": "AAPL", "close": 110, "sma_fast": 106, "sma_slow": 100,
    "rsi": 62, "atr_pct": 0.015, "volume_ratio": 1.4,
    "market_trend": 0.5, "news_score": 0.4,
}
BEAR = {
    "symbol": "AAPL", "close": 90, "sma_fast": 94, "sma_slow": 100,
    "rsi": 38, "atr_pct": 0.015, "volume_ratio": 1.5,
    "market_trend": -0.5, "news_score": -0.4,
}


class Tests(unittest.TestCase):
    def test_buy(self):
        result = decide(BULL)
        self.assertEqual(result.action, "BUY")
        self.assertFalse(result.order_submission_allowed)

    def test_sell(self):
        self.assertEqual(decide(BEAR).action, "SELL")

    def test_invalid_rsi(self):
        bad = dict(BULL, rsi=101)
        with self.assertRaises(ValueError):
            decide(bad)

    def test_high_volatility_regime(self):
        value = MarketInput.from_dict(dict(BULL, atr_pct=0.05))
        self.assertEqual(classify(value), "HIGH_VOLATILITY")

    def test_zero_orders(self):
        result = decide(BULL)
        self.assertEqual(result.actual_paper_orders_submitted, 0)
        self.assertEqual(result.actual_live_orders_submitted, 0)

    def test_deterministic(self):
        self.assertEqual(decide(BULL).to_dict(), decide(BULL).to_dict())


if __name__ == "__main__":
    unittest.main(verbosity=2)
