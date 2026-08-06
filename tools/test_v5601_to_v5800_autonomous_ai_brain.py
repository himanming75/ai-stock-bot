from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from autonomous_ai_brain.brain import (
    AutonomousAIBrain,
)
from autonomous_ai_brain.fixtures import (
    CANDIDATES,
)
from autonomous_ai_brain.service import (
    AutonomousAIBrainCertificationService,
)


class Tests(unittest.TestCase):
    def test_momentum_wins(self):
        decision, ranking = AutonomousAIBrain().decide(
            market_regime="BULL_TREND",
            candidates=CANDIDATES,
            system_health="HEALTHY",
            market_open=True,
            drawdown_guard_active=False,
        )
        self.assertEqual(
            decision.selected_strategy_id,
            "MOMENTUM",
        )
        self.assertEqual(ranking[0]["rank"], 1)

    def test_market_closed_waits(self):
        decision, _ = AutonomousAIBrain().decide(
            market_regime="BULL_TREND",
            candidates=CANDIDATES,
            system_health="HEALTHY",
            market_open=False,
            drawdown_guard_active=False,
        )
        self.assertEqual(decision.action, "WAIT")

    def test_drawdown_guard(self):
        decision, _ = AutonomousAIBrain().decide(
            market_regime="VOLATILE",
            candidates=CANDIDATES,
            system_health="HEALTHY",
            market_open=True,
            drawdown_guard_active=True,
        )
        self.assertEqual(
            decision.autonomous_state,
            "RISK_HOLD",
        )

    def test_critical_health_all_stop(self):
        decision, _ = AutonomousAIBrain().decide(
            market_regime="UNKNOWN",
            candidates=CANDIDATES,
            system_health="CRITICAL",
            market_open=True,
            drawdown_guard_active=False,
        )
        self.assertEqual(decision.action, "ALL_STOP")

    def test_no_automatic_promotion_or_order(self):
        decision, _ = AutonomousAIBrain().decide(
            market_regime="BULL_TREND",
            candidates=CANDIDATES,
            system_health="HEALTHY",
            market_open=True,
            drawdown_guard_active=False,
        )
        self.assertFalse(
            decision.automatic_promotion_performed
        )
        self.assertFalse(
            decision.order_submission_allowed
        )

    def test_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                AutonomousAIBrainCertificationService()
                .evaluate(
                    output_dir=Path(directory)
                )
            )
            self.assertEqual(result["status"], "PASS")

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                AutonomousAIBrainCertificationService()
                .evaluate(
                    output_dir=Path(directory)
                )
            )
            self.assertEqual(
                result["actual_paper_orders_submitted"],
                0,
            )
            self.assertEqual(
                result["actual_live_orders_submitted"],
                0,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
