from __future__ import annotations
import unittest
from ai_risk_allocation.position_sizing import size_positions


def payload(**updates):
    value = {
        "account_equity": 100000,
        "risk_per_trade_pct": 0.01,
        "maximum_position_pct": 0.25,
        "allow_fractional_shares": True,
        "minimum_notional": 1,
        "positions": [
            {
                "symbol": "AAPL",
                "sector": "TECH",
                "reference_price": 200,
                "stop_loss_pct": 0.04,
                "proposed_weight": 0.30,
            },
            {
                "symbol": "MSFT",
                "sector": "TECH",
                "reference_price": 500,
                "stop_loss_pct": 0.05,
                "proposed_weight": 0.20,
            },
        ],
    }
    value.update(updates)
    return value


class Tests(unittest.TestCase):
    def test_weight_cap(self):
        result = size_positions(payload())
        self.assertLessEqual(result.positions[0].effective_weight, 0.25)

    def test_risk_cap(self):
        result = size_positions(payload())
        self.assertLessEqual(result.positions[0].risk_at_stop, 1000.01)

    def test_fractional_quantity(self):
        result = size_positions(payload())
        self.assertGreater(result.positions[0].recommended_quantity, 0)

    def test_whole_share_mode(self):
        value = payload(allow_fractional_shares=False)
        result = size_positions(value)
        self.assertEqual(result.positions[0].recommended_quantity % 1, 0)

    def test_duplicate_symbol(self):
        value = payload()
        value["positions"].append(dict(value["positions"][0]))
        with self.assertRaises(ValueError):
            size_positions(value)

    def test_invalid_stop(self):
        value = payload()
        value["positions"][0]["stop_loss_pct"] = 0
        with self.assertRaises(ValueError):
            size_positions(value)

    def test_deterministic(self):
        self.assertEqual(size_positions(payload()).to_dict(), size_positions(payload()).to_dict())

    def test_zero_orders(self):
        result = size_positions(payload())
        self.assertFalse(result.order_submission_allowed)
        self.assertEqual(result.actual_paper_orders_submitted, 0)
        self.assertEqual(result.actual_live_orders_submitted, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
