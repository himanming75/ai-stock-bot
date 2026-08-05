from __future__ import annotations
import unittest

from autonomous_risk_governor.auto_pause import evaluate_auto_pause
from autonomous_risk_governor.auto_pause_guard import run_guard


def policy_result():
    return {
        "state": "RISK_POLICY_READY",
        "policy_hash": "a" * 64,
        "risk_operations_allowed": True,
        "validation": {"valid": True},
    }


def normal_guards():
    return {
        "daily_loss": {
            "state": "DAILY_LOSS_GUARD_ACTIVE",
            "status": "PASS",
            "risk_operations_allowed": True,
        },
        "drawdown": {
            "state": "MAX_DRAWDOWN_GUARD_ACTIVE",
            "status": "PASS",
            "risk_operations_allowed": True,
        },
        "position": {
            "state": "POSITION_SIZE_GUARD_ACTIVE",
            "status": "PASS",
            "risk_operations_allowed": True,
        },
        "exposure": {
            "state": "TOTAL_EXPOSURE_GUARD_ACTIVE",
            "status": "PASS",
            "risk_operations_allowed": True,
        },
        "concentration": {
            "state": "SYMBOL_CONCENTRATION_GUARD_ACTIVE",
            "status": "PASS",
            "risk_operations_allowed": True,
        },
        "kill_switch": {
            "state": "KILL_SWITCH_GUARD_STANDBY",
            "status": "PASS",
            "risk_operations_allowed": True,
        },
    }


class Tests(unittest.TestCase):
    def test_standby(self):
        result = evaluate_auto_pause(normal_guards())
        self.assertEqual(result["state"], "AUTO_PAUSE_STANDBY")
        self.assertFalse(result["pause_required"])

    def test_daily_loss_pause(self):
        guards = normal_guards()
        guards["daily_loss"] = {
            "state": "DAILY_LOSS_GUARD_PAUSE_REQUIRED",
            "status": "PASS",
            "risk_operations_allowed": False,
        }
        result = evaluate_auto_pause(guards)
        self.assertTrue(result["pause_required"])

    def test_kill_switch_pause(self):
        guards = normal_guards()
        guards["kill_switch"] = {
            "state": "KILL_SWITCH_GUARD_BLOCKED",
            "status": "PASS",
            "risk_operations_allowed": False,
        }
        result = evaluate_auto_pause(guards)
        self.assertTrue(result["pause_required"])

    def test_warning(self):
        guards = normal_guards()
        guards["exposure"] = {
            "state": "TOTAL_EXPOSURE_GUARD_WARNING",
            "status": "PASS",
            "risk_operations_allowed": True,
        }
        result = evaluate_auto_pause(guards)
        self.assertTrue(result["warning"])
        self.assertFalse(result["pause_required"])

    def test_failed_guard_pauses(self):
        guards = normal_guards()
        guards["position"]["status"] = "FAIL"
        result = evaluate_auto_pause(guards)
        self.assertTrue(result["pause_required"])

    def test_risk_operations_false_pauses(self):
        guards = normal_guards()
        guards["position"]["risk_operations_allowed"] = False
        result = evaluate_auto_pause(guards)
        self.assertTrue(result["pause_required"])

    def test_guard_pause_state(self):
        guards = normal_guards()
        guards["concentration"] = {
            "state": "SYMBOL_CONCENTRATION_GUARD_BLOCKED",
            "status": "PASS",
            "risk_operations_allowed": False,
        }
        result = run_guard(policy_result(), guards)
        self.assertEqual(result["state"], "AUTO_PAUSE_GUARD_PAUSED")
        self.assertEqual(result["pause_state"], "PAUSED")

    def test_zero_orders(self):
        result = run_guard(policy_result(), normal_guards())
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
