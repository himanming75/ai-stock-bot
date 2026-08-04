from __future__ import annotations
import unittest

from ai_risk_allocation.volatility import volatility_multiplier
from ai_risk_allocation.volatility_scaling import apply_volatility_scaling


def payload():
    return {
        "account_equity": 100000,
        "risk_per_trade_pct": 0.01,
        "maximum_position_pct": 0.25,
        "allow_fractional_shares": True,
        "minimum_notional": 1,
        "kelly_fraction": 0.5,
        "maximum_kelly_pct": 0.20,
        "target_volatility": 0.20,
        "minimum_volatility_multiplier": 0.25,
        "maximum_volatility_multiplier": 1.0,
        "positions": [
            {
                "symbol": "AAPL",
                "sector": "TECH",
                "reference_price": 200,
                "stop_loss_pct": 0.04,
                "proposed_weight": 0.25,
            }
        ],
        "kelly_statistics": [
            {
                "symbol": "AAPL",
                "win_rate": 0.60,
                "average_win": 0.08,
                "average_loss": 0.04,
            }
        ],
        "volatility_statistics": [
            {
                "symbol": "AAPL",
                "annualized_volatility": 0.40,
            }
        ],
    }


class Tests(unittest.TestCase):
    def test_multiplier_halves(self):
        self.assertAlmostEqual(volatility_multiplier(0.20, 0.40, 0.25, 1.0), 0.5)

    def test_multiplier_capped_at_one(self):
        self.assertEqual(volatility_multiplier(0.20, 0.10, 0.25, 1.0), 1.0)

    def test_minimum_multiplier(self):
        self.assertEqual(volatility_multiplier(0.20, 2.0, 0.25, 1.0), 0.25)

    def test_notional_scaled_down(self):
        result = apply_volatility_scaling(payload())
        self.assertLess(result["positions"][0]["recommended_notional"], 20000)

    def test_missing_stats(self):
        value = payload()
        value["volatility_statistics"] = []
        with self.assertRaises(ValueError):
            apply_volatility_scaling(value)

    def test_invalid_observed_volatility(self):
        value = payload()
        value["volatility_statistics"][0]["annualized_volatility"] = 0
        with self.assertRaises(ValueError):
            apply_volatility_scaling(value)

    def test_deterministic(self):
        self.assertEqual(apply_volatility_scaling(payload()), apply_volatility_scaling(payload()))

    def test_zero_orders(self):
        result = apply_volatility_scaling(payload())
        self.assertFalse(result["order_submission_allowed"])
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
