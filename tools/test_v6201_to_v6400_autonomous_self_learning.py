from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from autonomous_self_learning.analytics import (
    summarize_all,
)
from autonomous_self_learning.explainability import (
    build_decision_explanation,
)
from autonomous_self_learning.fixtures import (
    TRADES,
)
from autonomous_self_learning.service import (
    AutonomousSelfLearningCertificationService,
)


class Tests(unittest.TestCase):
    def test_strategy_summaries(self):
        summaries = summarize_all(TRADES)
        self.assertGreaterEqual(
            len(summaries),
            3,
        )

    def test_weak_strategy_detection(self):
        summaries = {
            item.strategy_id: item
            for item in summarize_all(TRADES)
        }
        self.assertIn(
            summaries["MEAN_REVERSION"].status,
            {"WEAK", "WATCH"},
        )

    def test_explanation(self):
        result = build_decision_explanation(
            symbol="NVDA",
            action="BUY",
            confidence="0.91",
            strategy_id="BREAKOUT",
            regime="BULL_TREND",
            safety_state="NORMAL",
            factors={"trend": "0.94"},
        )
        self.assertEqual(
            result["final_action"],
            "BUY",
        )

    def test_safety_override(self):
        result = build_decision_explanation(
            symbol="NVDA",
            action="BUY",
            confidence="0.91",
            strategy_id="BREAKOUT",
            regime="BULL_TREND",
            safety_state="RISK_HOLD",
            factors={"risk": "BREACHED"},
        )
        self.assertEqual(
            result["final_action"],
            "WAIT",
        )

    def test_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                AutonomousSelfLearningCertificationService()
                .evaluate(
                    output_dir=Path(directory)
                )
            )
            self.assertEqual(
                result["status"],
                "PASS",
            )

    def test_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            AutonomousSelfLearningCertificationService().evaluate(
                output_dir=root
            )
            self.assertTrue(
                (
                    root
                    / "autonomous_weekly_learning_report.json"
                ).exists()
            )
            self.assertTrue(
                (
                    root
                    / "autonomous_self_learning_ledger.jsonl"
                ).exists()
            )

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                AutonomousSelfLearningCertificationService()
                .evaluate(
                    output_dir=Path(directory)
                )
            )
            self.assertFalse(
                result[
                    "actual_broker_write_performed"
                ]
            )
            self.assertEqual(
                result[
                    "actual_paper_orders_submitted"
                ],
                0,
            )
            self.assertEqual(
                result[
                    "actual_live_orders_submitted"
                ],
                0,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
