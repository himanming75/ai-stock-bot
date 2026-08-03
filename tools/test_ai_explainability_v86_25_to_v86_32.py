from __future__ import annotations

import unittest

from explainability_engine.comparison import compare_ranked_candidates
from explainability_engine.contributions import (
    portfolio_contributions,
    signal_contributions,
)
from explainability_engine.engine import build_explainability_report
from explainability_engine.risks import (
    detect_portfolio_risks,
    detect_strategy_risks,
)


class ExplainabilityTests(unittest.TestCase):
    def setUp(self):
        self.strategy = {
            "decision": {
                "symbol": "AAPL",
                "decision": "BUY",
                "confidence": 82.1,
                "composite_score": 55.25,
                "bullish_count": 4,
                "bearish_count": 0,
                "neutral_count": 0,
                "reasons": ["MACD bullish", "EMA bullish"],
            }
        }
        self.indicators = {
            "indicators": {
                "symbol": "AAPL",
                "close": 154.82,
                "rsi_14": 100,
                "macd_histogram": -0.003,
                "atr_14": 1.05,
            }
        }
        self.portfolio = {
            "portfolio": {
                "ranked_count": 2,
                "portfolio_score": 54.65,
                "diversification_score": 80,
                "allocation_summary": {
                    "allocated_pct": 25,
                    "portfolio_exposure_limit_pct": 50,
                    "sector_limit_pct": 25,
                    "sector_allocations_pct": {"TECH": 25},
                },
                "ranked_candidates": [
                    {
                        "symbol": "AAPL",
                        "confidence": 82,
                        "risk_adjusted_score": 54,
                    },
                    {
                        "symbol": "MSFT",
                        "confidence": 78,
                        "risk_adjusted_score": 50,
                    },
                ],
                "recommended_allocations": [
                    {
                        "symbol": "AAPL",
                        "sector": "TECH",
                        "rank": 1,
                        "recommended_weight_pct": 15,
                        "risk_adjusted_score": 54,
                        "decision": "BUY",
                        "volatility_pct": 2,
                    },
                    {
                        "symbol": "MSFT",
                        "sector": "TECH",
                        "rank": 2,
                        "recommended_weight_pct": 10,
                        "risk_adjusted_score": 50,
                        "decision": "BUY",
                        "volatility_pct": 2,
                    },
                ],
            }
        }

    def test_signal_contributions(self):
        rows = signal_contributions(self.strategy)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["estimated_contribution_pct"], 50.0)

    def test_strategy_risk_detection(self):
        risks = detect_strategy_risks(self.strategy, self.indicators)
        codes = {row["code"] for row in risks}
        self.assertIn("RSI_OVERBOUGHT", codes)
        self.assertIn("MACD_DIVERGENCE", codes)

    def test_portfolio_contributions(self):
        rows = portfolio_contributions(self.portfolio)
        self.assertEqual(rows[0]["portfolio_contribution_pct"], 60.0)

    def test_candidate_comparison(self):
        rows = compare_ranked_candidates(self.portfolio)
        self.assertEqual(rows[0]["score_gap"], 4.0)

    def test_sector_risk_detection(self):
        risks = detect_portfolio_risks(self.portfolio)
        codes = {row["code"] for row in risks}
        self.assertIn("SECTOR_LIMIT_NEAR_CAP", codes)

    def test_report_contains_narratives(self):
        report = build_explainability_report(
            self.strategy,
            self.indicators,
            self.portfolio,
        )
        self.assertIn(
            "AAPL is classified as BUY",
            report["strategy_explanation"]["narrative"],
        )

    def test_limitations_present(self):
        report = build_explainability_report(
            self.strategy,
            self.indicators,
            self.portfolio,
        )
        self.assertGreaterEqual(len(report["limitations"]), 4)

    def test_safety_defaults(self):
        report = build_explainability_report(
            self.strategy,
            self.indicators,
            self.portfolio,
        )
        self.assertTrue(report["paper_only"])
        self.assertFalse(report["broker_write_enabled"])
        self.assertFalse(report["order_submission_enabled"])


if __name__ == "__main__":
    unittest.main()
