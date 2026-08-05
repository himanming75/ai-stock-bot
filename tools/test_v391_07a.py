from __future__ import annotations
import unittest

from autonomous_risk_governor.kill_switch import evaluate_kill_switch
from autonomous_risk_governor.kill_switch_guard import run_guard


def policy_result():
    return {
        "state": "RISK_POLICY_READY",
        "policy_hash": "a" * 64,
        "risk_operations_allowed": True,
        "validation": {"valid": True},
        "policy": {
            "kill_switch_required": True,
            "kill_switch_active": False,
            "manual_resume_required": True,
            "automatic_resume_enabled": False,
        },
    }


class Tests(unittest.TestCase):
    def test_standby(self):
        result = evaluate_kill_switch(True, False, True, False, True)
        self.assertEqual(result["state"], "KILL_SWITCH_STANDBY")
        self.assertTrue(result["effective_risk_operations_allowed"])

    def test_active_blocks(self):
        result = evaluate_kill_switch(True, True, True, False, False)
        self.assertEqual(result["state"], "KILL_SWITCH_ACTIVE")
        self.assertFalse(result["effective_risk_operations_allowed"])

    def test_active_with_operations_invalid(self):
        result = evaluate_kill_switch(True, True, True, False, True)
        self.assertFalse(result["valid"])

    def test_automatic_resume_rejected(self):
        result = evaluate_kill_switch(True, False, True, True, True)
        self.assertFalse(result["valid"])

    def test_manual_resume_required(self):
        result = evaluate_kill_switch(True, False, False, False, True)
        self.assertFalse(result["valid"])

    def test_guard_blocks(self):
        result = run_guard(
            policy_result(),
            {
                "kill_switch_active": True,
                "risk_operations_allowed": False,
            },
        )
        self.assertEqual(result["state"], "KILL_SWITCH_GUARD_BLOCKED")
        self.assertFalse(result["risk_operations_allowed"])

    def test_guard_standby(self):
        result = run_guard(
            policy_result(),
            {
                "kill_switch_active": False,
                "risk_operations_allowed": True,
            },
        )
        self.assertEqual(result["state"], "KILL_SWITCH_GUARD_STANDBY")
        self.assertTrue(result["risk_operations_allowed"])

    def test_zero_orders(self):
        result = run_guard(
            policy_result(),
            {
                "kill_switch_active": False,
                "risk_operations_allowed": True,
            },
        )
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
