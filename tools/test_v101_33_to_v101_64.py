import tempfile
import unittest
from pathlib import Path

from adaptive_rebalance.regime import normalize_regime, regime_multiplier
from adaptive_rebalance.costs import estimate_cost
from adaptive_rebalance.thresholds import adaptive_threshold
from adaptive_rebalance.optimizer import optimize_adjustments
from adaptive_rebalance.stability import stability_score
from adaptive_rebalance.gate import evaluate_gate
from adaptive_rebalance.engine import evaluate

class Tests(unittest.TestCase):
    def test_regime(self):
        value = normalize_regime({
            "primary_regime": "bull",
            "volatility_regime": "low_volatility",
            "confidence_score": 70,
        })
        self.assertEqual(value["primary_regime"], "BULL")

    def test_regime_multiplier(self):
        value = regime_multiplier(
            {
                "primary_regime": "BULL",
                "volatility_regime": "LOW_VOLATILITY",
                "confidence_score": 100,
            },
            {
                "regime_multipliers": {
                    "BULL": 0.9,
                    "LOW_VOLATILITY": 0.9,
                }
            },
        )
        self.assertAlmostEqual(value, 0.81)

    def test_cost(self):
        value = estimate_cost(
            10000,
            {"commission_bps": 0, "slippage_bps": 5, "spread_bps": 2},
        )
        self.assertEqual(value["estimated_cost"], 7)

    def test_threshold(self):
        value = adaptive_threshold(
            3, 4, 1.0, 7,
            {
                "volatility_reference_pct": 2,
                "volatility_sensitivity": 0.5,
                "cost_sensitivity": 0.02,
                "minimum_trigger_pct": 1.5,
                "maximum_trigger_pct": 8,
            },
        )
        self.assertGreater(value["adaptive_trigger_pct"], 3)

    def test_optimize(self):
        result = optimize_adjustments(
            {
                "account_equity": 100000,
                "snapshot": {
                    "drift_rows": [{
                        "strategy_id": "A",
                        "drift_pct": -10,
                        "absolute_drift_pct": 10,
                    }]
                },
            },
            1.0,
            {
                "base_rebalance_trigger_pct": 3,
                "base_incremental_fraction": 0.5,
                "minimum_incremental_fraction": 0.2,
                "maximum_incremental_fraction": 0.8,
                "minimum_net_benefit": 25,
                "strategy_metrics": [{
                    "strategy_id": "A",
                    "observed_volatility_pct": 2,
                }],
            },
        )
        self.assertEqual(result[0]["state"], "OPTIMIZED")
        self.assertFalse(result[0]["submission_allowed"])

    def test_stability(self):
        value = stability_score(
            [{"state": "OPTIMIZED"}],
            {
                "snapshot": {"largest_absolute_drift_pct": 5},
                "turnover_control": {"used_turnover_pct": 10},
                "cash_buffer_control": {"projected_cash_pct": 20},
            },
            {"minimum_stability_score": 40},
        )
        self.assertTrue(value["passed"])

    def test_gate(self):
        value = evaluate_gate(
            [{
                "state": "OPTIMIZED",
                "net_benefit": 100,
                "submission_allowed": False,
            }],
            {"passed": True},
            {"maximum_optimized_adjustments": 5},
        )
        self.assertTrue(value["passed"])

    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(
                evaluate(Path(temp))["state"],
                "ADAPTIVE_REBALANCE_SOURCE_REQUIRED",
            )

    def test_safety(self):
        with tempfile.TemporaryDirectory() as temp:
            self.assertFalse(evaluate(Path(temp))["order_submission_enabled"])

if __name__ == "__main__":
    unittest.main()
