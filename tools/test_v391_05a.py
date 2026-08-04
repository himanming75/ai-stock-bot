from __future__ import annotations
import unittest

from autonomous_risk_governor.exposure import (
    calculate_current_exposure,
    evaluate_total_exposure,
)
from autonomous_risk_governor.exposure_guard import run_guard


def policy_result():
    return {
        "state": "RISK_POLICY_READY",
        "policy_hash": "a" * 64,
        "risk_operations_allowed": True,
        "validation": {"valid": True},
        "policy": {
            "maximum_total_exposure_pct": 0.50,
        },
    }


def account():
    return {
        "equity": 100000,
        "status": "ACTIVE",
        "account_blocked": False,
        "trading_blocked": False,
    }


def positions():
    return [
        {"symbol": "AAPL", "market_value": 15000},
        {"symbol": "MSFT", "market_value": 10000},
        {"symbol": "SPY", "market_value": 5000},
    ]


class Tests(unittest.TestCase):
    def test_current_exposure_sum(self):
        self.assertEqual(float(calculate_current_exposure(positions())), 30000.0)

    def test_within_limit(self):
        result = evaluate_total_exposure(100000, positions(), 5000, 0.50)
        self.assertFalse(result["breached"])
        self.assertEqual(result["state"], "TOTAL_EXPOSURE_WITHIN_LIMIT")

    def test_breach(self):
        result = evaluate_total_exposure(100000, positions(), 25000, 0.50)
        self.assertTrue(result["breached"])

    def test_exact_limit_allowed(self):
        result = evaluate_total_exposure(100000, positions(), 20000, 0.50)
        self.assertFalse(result["breached"])

    def test_warning(self):
        result = evaluate_total_exposure(100000, positions(), 12000, 0.50)
        self.assertTrue(result["warning"])
        self.assertFalse(result["breached"])

    def test_short_market_value_counted_absolute(self):
        result = evaluate_total_exposure(
            100000,
            [{"symbol": "SHORT", "market_value": -10000}],
            0,
            0.50,
        )
        self.assertEqual(result["current_exposure"], 10000.0)

    def test_guard_blocks(self):
        result = run_guard(
            policy_result(),
            account(),
            positions(),
            {"symbol": "NVDA", "estimated_notional": 25000},
        )
        self.assertEqual(result["state"], "TOTAL_EXPOSURE_GUARD_BLOCKED")
        self.assertFalse(result["risk_operations_allowed"])

    def test_zero_orders(self):
        result = run_guard(
            policy_result(),
            account(),
            positions(),
            {"symbol": "NVDA", "estimated_notional": 5000},
        )
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
