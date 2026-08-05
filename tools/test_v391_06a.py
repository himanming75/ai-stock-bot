from __future__ import annotations
import unittest

from autonomous_risk_governor.concentration import (
    evaluate_symbol_concentration,
    symbol_market_value,
)
from autonomous_risk_governor.concentration_guard import run_guard


def policy_result():
    return {
        "state": "RISK_POLICY_READY",
        "policy_hash": "a" * 64,
        "risk_operations_allowed": True,
        "validation": {"valid": True},
        "policy": {
            "maximum_symbol_exposure_pct": 0.10,
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
        {"symbol": "AAPL", "market_value": 6000},
        {"symbol": "MSFT", "market_value": 10000},
        {"symbol": "SPY", "market_value": 5000},
    ]


class Tests(unittest.TestCase):
    def test_symbol_value(self):
        self.assertEqual(float(symbol_market_value(positions(), "AAPL")), 6000.0)

    def test_within_limit(self):
        result = evaluate_symbol_concentration(
            100000, positions(), "AAPL", 1000, 0.10
        )
        self.assertFalse(result["breached"])

    def test_breach(self):
        result = evaluate_symbol_concentration(
            100000, positions(), "AAPL", 5000, 0.10
        )
        self.assertTrue(result["breached"])

    def test_exact_limit_allowed(self):
        result = evaluate_symbol_concentration(
            100000, positions(), "AAPL", 4000, 0.10
        )
        self.assertFalse(result["breached"])

    def test_warning(self):
        result = evaluate_symbol_concentration(
            100000, positions(), "AAPL", 2500, 0.10
        )
        self.assertTrue(result["warning"])
        self.assertFalse(result["breached"])

    def test_new_symbol(self):
        result = evaluate_symbol_concentration(
            100000, positions(), "NVDA", 5000, 0.10
        )
        self.assertEqual(result["current_symbol_value"], 0.0)

    def test_guard_blocks(self):
        result = run_guard(
            policy_result(),
            account(),
            positions(),
            {"symbol": "AAPL", "estimated_notional": 5000},
        )
        self.assertEqual(result["state"], "SYMBOL_CONCENTRATION_GUARD_BLOCKED")
        self.assertFalse(result["risk_operations_allowed"])

    def test_zero_orders(self):
        result = run_guard(
            policy_result(),
            account(),
            positions(),
            {"symbol": "AAPL", "estimated_notional": 1000},
        )
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
