from __future__ import annotations
from decimal import Decimal
import unittest

from ai_intelligence.events import (
    EarningsEventFramework,
    EventScoringFramework,
)
from ai_intelligence.historical_adapter import HistoricalDataAdapter
from ai_intelligence.indicators import TechnicalIndicatorEngine
from ai_intelligence.regime import MarketRegimeDetector
from ai_intelligence.scanner import StockScanner


class Tests(unittest.TestCase):
    def test_indicators_created(self):
        bars = HistoricalDataAdapter().fixture_bars(
            start_price=Decimal("100")
        )
        result = TechnicalIndicatorEngine().calculate(bars)
        self.assertIn("rsi_14", result)
        self.assertIn("atr_14", result)

    def test_bull_regime(self):
        result = MarketRegimeDetector().detect({
            "index_return_20": "0.06",
            "volatility_20": "0.10",
            "breadth": "0.70",
            "trend_strength": "0.80",
        })
        self.assertEqual(result["regime"], "BULL_TREND")

    def test_event_framework_is_offline(self):
        result = EventScoringFramework().score([
            {
                "sentiment": "0.5",
                "severity": "HIGH",
            }
        ])
        self.assertFalse(result["external_news_api_used"])

    def test_imminent_earnings_blocks(self):
        result = EarningsEventFramework().evaluate(
            days_until_earnings=1,
            surprise_history=Decimal("0"),
        )
        self.assertTrue(result["block_new_position"])

    def test_scanner_scores(self):
        bars = HistoricalDataAdapter().fixture_bars(
            start_price=Decimal("100")
        )
        result = StockScanner().score_symbol(
            symbol="AAPL",
            bars=bars,
            sector_score=Decimal("0.8"),
            event_score=Decimal("0.7"),
            regime_multiplier=Decimal("1"),
        )
        self.assertGreater(Decimal(result["total_score"]), Decimal("0"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
