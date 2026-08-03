from __future__ import annotations

import unittest

from backtest_v2.models import Bar
from validation_v2.engine import run_validation
from validation_v2.monte_carlo import run_monte_carlo
from validation_v2.overfit import calculate_overfit_risk
from validation_v2.stress import mutate_bars, run_stress_tests
from validation_v2.walk_forward import run_walk_forward


def bars(count=240):
    output = []
    close = 100.0
    for i in range(count):
        if i % 48 < 24:
            close += 0.7
        else:
            close -= 0.5
        output.append(Bar(
            timestamp=f"2026-{(i//28)%12+1:02d}-{(i%28)+1:02d}",
            open=close - 0.2,
            high=close + 0.7,
            low=close - 0.7,
            close=close,
            volume=100000 + i * 100,
        ))
    return output


def policy():
    return {
        "train_size": 100,
        "test_size": 40,
        "step_size": 40,
        "minimum_walk_forward_windows": 2,
        "minimum_positive_window_pct": 0,
        "minimum_stress_return_pct": -100,
        "maximum_stress_drawdown_pct": 100,
        "maximum_overfit_risk_score": 100,
        "maximum_loss_probability_pct": 100,
        "monte_carlo_iterations": 100,
        "backtest_policy": {
            "initial_cash": 100000,
            "position_fraction": 0.9,
            "fast_period": 5,
            "slow_period": 15,
            "commission_bps": 1,
            "slippage_bps": 2,
        },
    }


class WalkForwardStressTests(unittest.TestCase):
    def test_walk_forward_windows(self):
        result = run_walk_forward("AAPL", bars(), policy())
        self.assertGreaterEqual(result["window_count"], 2)

    def test_missing_data_reduces_bars(self):
        mutated = mutate_bars(bars(), "missing_data")
        self.assertLess(len(mutated), len(bars()))

    def test_stress_scenarios(self):
        result = run_stress_tests("AAPL", bars(), policy())
        self.assertEqual(result["scenario_count"], 5)

    def test_monte_carlo_deterministic(self):
        trades = [{"net_pnl": 100}, {"net_pnl": -50}]
        a = run_monte_carlo(trades, iterations=50, seed=1)
        b = run_monte_carlo(trades, iterations=50, seed=1)
        self.assertEqual(a, b)

    def test_overfit_score_bounds(self):
        result = calculate_overfit_risk(
            {"total_return_pct": 20},
            {"average_test_return_pct": 10, "positive_window_pct": 50},
            {"worst_return_pct": -5},
        )
        self.assertGreaterEqual(result["overfit_risk_score"], 0)
        self.assertLessEqual(result["overfit_risk_score"], 100)

    def test_validation_certificate(self):
        result = run_validation("AAPL", bars(), policy())
        self.assertEqual(len(result["certificate"]["certificate_sha256"]), 64)

    def test_validation_safety(self):
        result = run_validation("AAPL", bars(), policy())
        self.assertTrue(result["paper_only"])
        self.assertFalse(result["broker_write_enabled"])

    def test_validation_checks_present(self):
        result = run_validation("AAPL", bars(), policy())
        self.assertGreaterEqual(len(result["robustness_checks"]), 6)


if __name__ == "__main__":
    unittest.main()
