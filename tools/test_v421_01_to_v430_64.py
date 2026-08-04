from __future__ import annotations
import unittest
from ai_portfolio_intelligence.engine import build_portfolio


def make_bars(direction: int):
    result = []
    price = 100.0
    for i in range(30):
        close = price + float(direction)
        result.append({
            "open": price,
            "high": max(price, close) + 0.4,
            "low": min(price, close) - 0.4,
            "close": close,
            "volume": 1000 + i * 20,
        })
        price = close
    return result


def payload():
    return {
        "maximum_positions": 3,
        "maximum_positions_per_sector": 1,
        "minimum_confidence": 55,
        "maximum_risk_score": 65,
        "maximum_single_weight": 0.4,
        "candidates": [
            {"symbol": "AAA", "sector": "TECH", "bars": make_bars(1), "market_trend": 0.8, "news_score": 0.5, "liquidity_score": 90},
            {"symbol": "BBB", "sector": "TECH", "bars": make_bars(1), "market_trend": 0.7, "news_score": 0.4, "liquidity_score": 80},
            {"symbol": "CCC", "sector": "HEALTH", "bars": make_bars(1), "market_trend": 0.6, "news_score": 0.3, "liquidity_score": 75},
            {"symbol": "DDD", "sector": "ENERGY", "bars": make_bars(-1), "market_trend": -0.5, "news_score": -0.4, "liquidity_score": 70},
        ]
    }


class Tests(unittest.TestCase):
    def test_build(self):
        result = build_portfolio(payload())
        self.assertGreaterEqual(len(result.selected), 1)
        self.assertFalse(result.order_submission_allowed)

    def test_sector_cap(self):
        result = build_portfolio(payload())
        tech = [item for item in result.selected if item.sector == "TECH"]
        self.assertLessEqual(len(tech), 1)

    def test_weights(self):
        result = build_portfolio(payload())
        self.assertAlmostEqual(result.total_selected_weight + result.cash_weight, 1.0, places=4)

    def test_maximum_positions(self):
        result = build_portfolio(payload())
        self.assertLessEqual(len(result.selected), 3)

    def test_exclusion_reason(self):
        result = build_portfolio(payload())
        self.assertTrue(any(item.exclusion_reasons for item in result.excluded))

    def test_duplicate_symbol(self):
        value = payload()
        value["candidates"].append(dict(value["candidates"][0]))
        with self.assertRaises(ValueError):
            build_portfolio(value)

    def test_deterministic(self):
        self.assertEqual(build_portfolio(payload()).to_dict(), build_portfolio(payload()).to_dict())

    def test_zero_orders(self):
        result = build_portfolio(payload())
        self.assertEqual(result.actual_paper_orders_submitted, 0)
        self.assertEqual(result.actual_live_orders_submitted, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
