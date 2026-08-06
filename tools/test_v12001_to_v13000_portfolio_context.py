from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from portfolio_context_ai.correlation import (
    classify_correlation,
    correlation_matrix,
    pearson,
)
from portfolio_context_ai.feedback import build_signal_feedback
from portfolio_context_ai.performance import performance_metrics
from portfolio_context_ai.portfolio import build_portfolio_context
from portfolio_context_ai.service import (
    PortfolioContextCertificationService,
    _fallback_analyses,
    _offline_returns,
)


class Tests(unittest.TestCase):
    def test_pearson(self):
        self.assertAlmostEqual(pearson([1, 2, 3], [2, 4, 6]), 1.0)
        self.assertAlmostEqual(pearson([1, 2, 3], [6, 4, 2]), -1.0)

    def test_correlation_classification(self):
        self.assertEqual(classify_correlation(0.7), "POSITIVE")
        self.assertEqual(classify_correlation(-0.7), "NEGATIVE")
        self.assertEqual(classify_correlation(0.1), "NEUTRAL")

    def test_matrix(self):
        matrix = correlation_matrix(_offline_returns())
        self.assertEqual(matrix["AAPL"]["AAPL"], 1.0)
        self.assertEqual(matrix["AAPL"]["MSFT"], matrix["MSFT"]["AAPL"])

    def test_portfolio_context(self):
        analyses = _fallback_analyses()
        matrix = correlation_matrix(_offline_returns())
        result = build_portfolio_context(analyses, matrix)
        self.assertEqual(result["pair_count"], 6)
        self.assertFalse(result["capital_allocation_enabled"])

    def test_feedback(self):
        result = build_signal_feedback(
            _fallback_analyses(),
            _offline_returns(),
        )
        self.assertEqual(len(result["rows"]), 4)
        self.assertFalse(result["automatic_model_update_enabled"])
        self.assertFalse(result["live_learning_enabled"])

    def test_performance(self):
        result = performance_metrics([0.01, -0.005, 0.008, 0.002])
        self.assertEqual(result["count"], 4)
        self.assertGreaterEqual(result["win_rate"], 0.0)
        self.assertGreaterEqual(result["max_drawdown"], 0.0)

    def test_certification(self):
        with tempfile.TemporaryDirectory() as d:
            result = PortfolioContextCertificationService().evaluate(
                output_dir=Path(d)
            )
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["cross_asset_correlation_ready"])
            self.assertTrue(result["signal_feedback_ready"])
            self.assertTrue(result["offline_performance_analytics_ready"])

    def test_zero_action_contract(self):
        with tempfile.TemporaryDirectory() as d:
            result = PortfolioContextCertificationService().evaluate(
                output_dir=Path(d)
            )
            self.assertFalse(result["actual_broker_write_performed"])
            self.assertFalse(result["actual_position_allocation_performed"])
            self.assertFalse(result["actual_model_weight_update_performed"])
            self.assertFalse(result["actual_live_learning_performed"])
            self.assertEqual(result["actual_paper_orders_submitted"], 0)
            self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
