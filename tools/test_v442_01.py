from __future__ import annotations
import unittest

from ai_risk_allocation.kelly import full_kelly
from ai_risk_allocation.kelly_sizing import apply_kelly


def payload():
    return {
        "account_equity": 100000,
        "risk_per_trade_pct": 0.01,
        "maximum_position_pct": 0.25,
        "allow_fractional_shares": True,
        "minimum_notional": 1,
        "kelly_fraction": 0.5,
        "maximum_kelly_pct": 0.20,
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
    }


class Tests(unittest.TestCase):
    def test_full_kelly(self):
        self.assertAlmostEqual(full_kelly(0.60, 0.08, 0.04), 0.40, places=6)

    def test_fractional_kelly_cap(self):
        result = apply_kelly(payload())
        self.assertLessEqual(result["positions"][0]["capped_kelly_pct"], 0.20)

    def test_kelly_limits_notional(self):
        value = payload()
        value["maximum_kelly_pct"] = 0.10
        result = apply_kelly(value)
        self.assertLessEqual(result["positions"][0]["recommended_notional"], 10000.01)

    def test_missing_stats(self):
        value = payload()
        value["kelly_statistics"] = []
        with self.assertRaises(ValueError):
            apply_kelly(value)

    def test_invalid_win_rate(self):
        value = payload()
        value["kelly_statistics"][0]["win_rate"] = 1.1
        with self.assertRaises(ValueError):
            apply_kelly(value)

    def test_negative_edge_zero(self):
        self.assertEqual(full_kelly(0.30, 0.04, 0.08), 0.0)

    def test_deterministic(self):
        self.assertEqual(apply_kelly(payload()), apply_kelly(payload()))

    def test_zero_orders(self):
        result = apply_kelly(payload())
        self.assertFalse(result["order_submission_allowed"])
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
