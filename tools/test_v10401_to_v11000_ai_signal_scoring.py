from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from ai_signal_scoring.backtest import backtest_bridge
from ai_signal_scoring.ensemble import score_candidate
from ai_signal_scoring.position_size import recommend_position_size
from ai_signal_scoring.service import AISignalScoringCertificationService


class Tests(unittest.TestCase):
    def candidate(self):
        return {
            "symbol": "AAPL",
            "action": "BUY",
            "score": 30,
            "confidence": 40,
            "regime": "REGIME_TRENDING",
            "trend": "TREND_UP",
            "risk_gate": "PASS_READ_ONLY",
            "features": {
                "close": 100,
                "ema9": 102,
                "ema21": 98,
                "rsi14": 60,
                "momentum_5": 0.02,
                "volume_ratio": 1.4,
                "atr_percent": 0.01,
                "bollinger_width": 0.04,
            },
            "conflict_analysis": {
                "conflict_count": 0,
                "conflicts": [],
            },
        }

    def test_ensemble_score(self):
        result = score_candidate(self.candidate())
        self.assertGreater(result["ai_score"], 0)
        self.assertLessEqual(result["ai_score"], 100)

    def test_conflict_penalty(self):
        clean = self.candidate()
        conflicted = self.candidate()
        conflicted["conflict_analysis"] = {
            "conflict_count": 2,
            "conflicts": [{}, {}],
        }
        self.assertGreater(
            score_candidate(clean)["ai_score"],
            score_candidate(conflicted)["ai_score"],
        )

    def test_position_size_candidate_only(self):
        result = recommend_position_size(
            ai_score=80,
            confidence=70,
            risk_component=90,
            max_position_percent=10,
        )
        self.assertFalse(result["position_order_enabled"])
        self.assertFalse(result["capital_allocation_enabled"])

    def test_backtest_bridge(self):
        result = backtest_bridge(
            prices=[100, 101, 102, 101, 103],
            actions=["BUY", "BUY", "SELL", "BUY", "HOLD"],
        )
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["order_submission_enabled"])

    def test_certification(self):
        with tempfile.TemporaryDirectory() as d:
            result = AISignalScoringCertificationService().evaluate(
                output_dir=Path(d)
            )
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["weighted_ensemble_ready"])
            self.assertTrue(result["backtest_bridge_ready"])

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as d:
            result = AISignalScoringCertificationService().evaluate(
                output_dir=Path(d)
            )
            self.assertFalse(result["actual_broker_write_performed"])
            self.assertFalse(result["actual_position_allocation_performed"])
            self.assertEqual(result["actual_paper_orders_submitted"], 0)
            self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
