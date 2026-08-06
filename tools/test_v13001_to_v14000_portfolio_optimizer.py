from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from portfolio_optimizer_ai.guardrails import evaluate_guardrails
from portfolio_optimizer_ai.optimizer import build_candidate_weights
from portfolio_optimizer_ai.service import (
    PortfolioOptimizerCertificationService,
    _fallback_analyses,
)
from portfolio_optimizer_ai.stress import run_stress_scenarios


class Tests(unittest.TestCase):
    def test_candidate_weights(self):
        result = build_candidate_weights(_fallback_analyses())
        self.assertAlmostEqual(result["weight_sum"], 1.0, places=5)
        self.assertFalse(result["capital_allocation_enabled"])
        self.assertFalse(result["order_generation_enabled"])

    def test_weight_cap(self):
        result = build_candidate_weights(
            _fallback_analyses(),
            max_symbol_weight=0.35,
        )
        self.assertLessEqual(
            max(result["candidate_weights"].values()),
            0.40,
        )

    def test_stress_scenarios(self):
        optimizer = build_candidate_weights(_fallback_analyses())
        results = run_stress_scenarios(
            _fallback_analyses(),
            optimizer["candidate_weights"],
            0.65,
        )
        self.assertEqual(len(results), 5)
        self.assertTrue(all(item["simulation_only"] for item in results))

    def test_guardrails(self):
        optimizer = build_candidate_weights(_fallback_analyses())
        stress = run_stress_scenarios(
            _fallback_analyses(),
            optimizer["candidate_weights"],
            0.65,
        )
        result = evaluate_guardrails(
            weights=optimizer["candidate_weights"],
            stress_results=stress,
            average_abs_correlation=0.65,
        )
        self.assertIn(result["status"], {"PASS", "BLOCKED"})
        self.assertFalse(result["capital_lock_enabled"])
        self.assertFalse(result["broker_write_enabled"])

    def test_strict_guardrail_blocks(self):
        result = evaluate_guardrails(
            weights={"A": 0.8, "B": 0.2},
            stress_results=[{
                "estimated_drawdown": 0.20,
                "portfolio_risk": 0.15,
            }],
            average_abs_correlation=0.95,
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertGreaterEqual(len(result["breaches"]), 3)

    def test_certification(self):
        with tempfile.TemporaryDirectory() as d:
            result = PortfolioOptimizerCertificationService().evaluate(
                output_dir=Path(d)
            )
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["scenario_stress_testing_ready"])
            self.assertTrue(result["capital_guardrail_simulation_ready"])

    def test_zero_action_contract(self):
        with tempfile.TemporaryDirectory() as d:
            result = PortfolioOptimizerCertificationService().evaluate(
                output_dir=Path(d)
            )
            self.assertFalse(result["actual_broker_write_performed"])
            self.assertFalse(result["actual_position_allocation_performed"])
            self.assertFalse(result["actual_capital_lock_performed"])
            self.assertFalse(result["actual_order_submission_performed"])
            self.assertEqual(result["actual_paper_orders_submitted"], 0)
            self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
