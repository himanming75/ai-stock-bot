from __future__ import annotations
from decimal import Decimal
import unittest

from ai_operations_v3.marketplace import StrategyMarketplace
from ai_operations_v3.metrics import PerformanceMetricsEngine
from ai_operations_v3.portfolio import PortfolioIntelligence


class Tests(unittest.TestCase):
    def test_metrics(self):
        result = PerformanceMetricsEngine().calculate(
            trade_returns=[Decimal("0.01"), Decimal("-0.005")],
            trade_pnls=[Decimal("10"), Decimal("-5")],
            equity_curve=[Decimal("100"), Decimal("110"), Decimal("105")],
        )
        self.assertEqual(result["trade_count"], 2)
        self.assertEqual(result["win_rate"], "0.5000")

    def test_marketplace_has_eight_strategies(self):
        result = StrategyMarketplace().build(strategy_ranking=[])
        self.assertEqual(result["strategy_count"], 8)
        self.assertFalse(result["actual_strategy_activation_performed"])

    def test_portfolio_preview_no_orders(self):
        result = PortfolioIntelligence().analyze(
            positions=[
                {"symbol": "A", "sector": "Tech", "market_value": "50"},
                {"symbol": "B", "sector": "Health", "market_value": "50"},
            ],
            correlations={
                "A": {"A": Decimal("1"), "B": Decimal("0.2")},
                "B": {"A": Decimal("0.2"), "B": Decimal("1")},
            },
            sector_limits={
                "Tech": Decimal("0.6"),
                "Health": Decimal("0.6"),
            },
        )
        self.assertFalse(result["actual_orders_created"])

    def test_diversification_score_bounded(self):
        result = PortfolioIntelligence().analyze(
            positions=[
                {"symbol": "A", "sector": "Tech", "market_value": "100"},
            ],
            correlations={"A": {"A": Decimal("1")}},
            sector_limits={"Tech": Decimal("1")},
        )
        score = Decimal(result["diversification_score"])
        self.assertGreaterEqual(score, Decimal("0"))
        self.assertLessEqual(score, Decimal("1"))

    def test_marketplace_preview_only(self):
        result = StrategyMarketplace().build(strategy_ranking=[
            {"strategy_id": "momentum_v2", "total_score": "0.8"}
        ])
        self.assertTrue(result["configuration_preview_only"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
