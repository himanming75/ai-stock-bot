from __future__ import annotations
import unittest

from autonomous_risk_governor.daily_loss import evaluate_daily_loss
from autonomous_risk_governor.daily_loss_guard import run_guard


def policy_result():
    return {
        "state": "RISK_POLICY_READY",
        "policy_hash": "a" * 64,
        "risk_operations_allowed": True,
        "validation": {"valid": True},
        "policy": {
            "daily_loss_limit_pct": 0.02,
        },
    }


def account(equity=99000, last_equity=100000):
    return {
        "equity": equity,
        "last_equity": last_equity,
        "status": "ACTIVE",
        "account_blocked": False,
        "trading_blocked": False,
    }


class Tests(unittest.TestCase):
    def test_within_limit(self):
        result = evaluate_daily_loss(99000, 100000, 0.02)
        self.assertFalse(result["breached"])
        self.assertEqual(result["state"], "DAILY_LOSS_WITHIN_LIMIT")

    def test_breach_at_limit(self):
        result = evaluate_daily_loss(98000, 100000, 0.02)
        self.assertTrue(result["breached"])
        self.assertEqual(result["required_action"], "PAUSE_REQUIRED")

    def test_breach_below_limit(self):
        result = evaluate_daily_loss(97000, 100000, 0.02)
        self.assertTrue(result["breached"])

    def test_warning_at_75_percent(self):
        result = evaluate_daily_loss(98500, 100000, 0.02)
        self.assertTrue(result["warning"])
        self.assertFalse(result["breached"])

    def test_gain_has_zero_loss(self):
        result = evaluate_daily_loss(101000, 100000, 0.02)
        self.assertEqual(result["daily_loss_pct"], 0.0)

    def test_invalid_last_equity(self):
        with self.assertRaises(ValueError):
            evaluate_daily_loss(1000, 0, 0.02)

    def test_guard_pause(self):
        result = run_guard(policy_result(), account(97000, 100000))
        self.assertTrue(result["pause_required"])
        self.assertFalse(result["risk_operations_allowed"])

    def test_zero_orders(self):
        result = run_guard(policy_result(), account())
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
