from __future__ import annotations
import unittest

from autonomous_risk_governor.position_limit import evaluate_position_limit
from autonomous_risk_governor.position_limit_guard import run_guard


def policy_result():
    return {
        "state": "RISK_POLICY_READY",
        "policy_hash": "a" * 64,
        "risk_operations_allowed": True,
        "validation": {"valid": True},
        "policy": {
            "maximum_position_pct": 0.10,
        },
    }


def account():
    return {
        "equity": 100000,
        "status": "ACTIVE",
        "account_blocked": False,
        "trading_blocked": False,
    }


class Tests(unittest.TestCase):
    def test_within_limit(self):
        result = evaluate_position_limit(100000, 5000, 2000, 0.10)
        self.assertFalse(result["breached"])
        self.assertEqual(result["state"], "POSITION_LIMIT_WITHIN_LIMIT")

    def test_breach(self):
        result = evaluate_position_limit(100000, 9000, 2000, 0.10)
        self.assertTrue(result["breached"])
        self.assertEqual(result["required_action"], "BLOCK_NEW_POSITION_RISK")

    def test_exact_limit_allowed(self):
        result = evaluate_position_limit(100000, 9000, 1000, 0.10)
        self.assertFalse(result["breached"])

    def test_warning(self):
        result = evaluate_position_limit(100000, 7500, 1000, 0.10)
        self.assertTrue(result["warning"])
        self.assertFalse(result["breached"])

    def test_remaining_capacity(self):
        result = evaluate_position_limit(100000, 6000, 1000, 0.10)
        self.assertEqual(result["remaining_capacity"], 4000.0)

    def test_invalid_equity(self):
        with self.assertRaises(ValueError):
            evaluate_position_limit(0, 1000, 100, 0.10)

    def test_guard_blocks(self):
        result = run_guard(
            policy_result(),
            account(),
            {"symbol": "AAPL", "market_value": 9500},
            {"symbol": "AAPL", "estimated_notional": 1000},
        )
        self.assertEqual(result["state"], "POSITION_SIZE_GUARD_BLOCKED")
        self.assertFalse(result["risk_operations_allowed"])

    def test_zero_orders(self):
        result = run_guard(
            policy_result(),
            account(),
            {"symbol": "AAPL", "market_value": 5000},
            {"symbol": "AAPL", "estimated_notional": 1000},
        )
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
