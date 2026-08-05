from __future__ import annotations
import unittest

from autonomous_risk_governor.drawdown import evaluate_drawdown
from autonomous_risk_governor.drawdown_guard import run_guard


def policy_result():
    return {
        "state": "RISK_POLICY_READY",
        "policy_hash": "a" * 64,
        "risk_operations_allowed": True,
        "validation": {"valid": True},
        "policy": {
            "maximum_drawdown_pct": 0.10,
        },
    }


def account(equity=95000):
    return {
        "equity": equity,
        "status": "ACTIVE",
        "account_blocked": False,
        "trading_blocked": False,
    }


class Tests(unittest.TestCase):
    def test_within_limit(self):
        result = evaluate_drawdown(95000, 100000, 0.10)
        self.assertFalse(result["breached"])
        self.assertEqual(result["state"], "MAX_DRAWDOWN_WITHIN_LIMIT")

    def test_breach_at_limit(self):
        result = evaluate_drawdown(90000, 100000, 0.10)
        self.assertTrue(result["breached"])

    def test_warning_at_75_percent(self):
        result = evaluate_drawdown(92500, 100000, 0.10)
        self.assertTrue(result["warning"])
        self.assertFalse(result["breached"])

    def test_new_peak(self):
        result = evaluate_drawdown(105000, 100000, 0.10)
        self.assertTrue(result["new_peak_recorded"])
        self.assertEqual(result["drawdown_pct"], 0.0)

    def test_invalid_peak(self):
        with self.assertRaises(ValueError):
            evaluate_drawdown(1000, 0, 0.10)

    def test_guard_pause(self):
        result = run_guard(
            policy_result(),
            account(85000),
            {"peak_equity": 100000},
        )
        self.assertTrue(result["pause_required"])
        self.assertFalse(result["risk_operations_allowed"])

    def test_guard_active(self):
        result = run_guard(
            policy_result(),
            account(97000),
            {"peak_equity": 100000},
        )
        self.assertEqual(result["state"], "MAX_DRAWDOWN_GUARD_ACTIVE")

    def test_zero_orders(self):
        result = run_guard(
            policy_result(),
            account(),
            {"peak_equity": 100000},
        )
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
