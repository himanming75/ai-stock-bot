from __future__ import annotations
import unittest
from ai_strategy_selection.engine import select_strategy


def payload(**updates):
    value = {
        "market_regime": "BULL_TREND",
        "trend_strength": 82,
        "momentum_strength": 76,
        "breakout_strength": 68,
        "mean_reversion_strength": 25,
        "volatility_score": 34,
        "liquidity_score": 88,
        "breadth_score": 74,
        "portfolio_score": 72,
        "minimum_portfolio_score": 55,
    }
    value.update(updates)
    return value


class Tests(unittest.TestCase):
    def test_trend_or_momentum_selected(self):
        result = select_strategy(payload())
        self.assertIn(result.selected_strategy, {"TREND_FOLLOWING", "MOMENTUM", "BREAKOUT"})

    def test_high_volatility_defensive(self):
        result = select_strategy(payload(
            market_regime="HIGH_VOLATILITY",
            volatility_score=95,
            liquidity_score=40,
            breadth_score=20,
            portfolio_score=30,
        ))
        self.assertEqual(result.selected_strategy, "CASH_DEFENSIVE")

    def test_range_mean_reversion(self):
        result = select_strategy(payload(
            market_regime="RANGE",
            trend_strength=20,
            momentum_strength=30,
            breakout_strength=25,
            mean_reversion_strength=90,
            volatility_score=25,
        ))
        self.assertEqual(result.selected_strategy, "MEAN_REVERSION")

    def test_invalid_regime(self):
        with self.assertRaises(ValueError):
            select_strategy(payload(market_regime="UNKNOWN"))

    def test_score_range(self):
        result = select_strategy(payload())
        self.assertTrue(all(0 <= item.score <= 100 for item in result.strategy_scores))

    def test_deterministic(self):
        self.assertEqual(select_strategy(payload()).to_dict(), select_strategy(payload()).to_dict())

    def test_zero_orders(self):
        result = select_strategy(payload())
        self.assertEqual(result.actual_paper_orders_submitted, 0)
        self.assertEqual(result.actual_live_orders_submitted, 0)

    def test_order_submission_blocked(self):
        self.assertFalse(select_strategy(payload()).order_submission_allowed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
