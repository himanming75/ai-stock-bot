from __future__ import annotations
import copy
import unittest

from autonomous_risk_governor.integration import evaluate_integration
from autonomous_risk_governor.integration_guard import run_guard


HASH = "a" * 64


def normal_results():
    return {
        "policy": {
            "stage": "V391.01A",
            "state": "RISK_POLICY_READY",
            "status": "PASS",
            "policy_hash": HASH,
            "risk_operations_allowed": True,
        },
        "daily_loss": {
            "stage": "V391.02A",
            "state": "DAILY_LOSS_GUARD_ACTIVE",
            "status": "PASS",
            "policy_hash": HASH,
            "risk_operations_allowed": True,
        },
        "drawdown": {
            "stage": "V391.03A",
            "state": "MAX_DRAWDOWN_GUARD_ACTIVE",
            "status": "PASS",
            "policy_hash": HASH,
            "risk_operations_allowed": True,
        },
        "position": {
            "stage": "V391.04A",
            "state": "POSITION_SIZE_GUARD_ACTIVE",
            "status": "PASS",
            "policy_hash": HASH,
            "risk_operations_allowed": True,
        },
        "exposure": {
            "stage": "V391.05A",
            "state": "TOTAL_EXPOSURE_GUARD_ACTIVE",
            "status": "PASS",
            "policy_hash": HASH,
            "risk_operations_allowed": True,
        },
        "concentration": {
            "stage": "V391.06A",
            "state": "SYMBOL_CONCENTRATION_GUARD_ACTIVE",
            "status": "PASS",
            "policy_hash": HASH,
            "risk_operations_allowed": True,
        },
        "kill_switch": {
            "stage": "V391.07A",
            "state": "KILL_SWITCH_GUARD_STANDBY",
            "status": "PASS",
            "policy_hash": HASH,
            "risk_operations_allowed": True,
        },
        "auto_pause": {
            "stage": "V391.08A",
            "state": "AUTO_PAUSE_GUARD_STANDBY",
            "status": "PASS",
            "policy_hash": HASH,
            "risk_operations_allowed": True,
        },
        "manual_resume": {
            "stage": "V391.09A",
            "state": "MANUAL_RESUME_GUARD_APPROVED",
            "status": "PASS",
            "policy_hash": HASH,
            "risk_operations_allowed": True,
        },
    }


class Tests(unittest.TestCase):
    def test_ready(self):
        result = evaluate_integration(normal_results())
        self.assertEqual(result["decision"], "ALLOW")

    def test_warning(self):
        values = normal_results()
        values["exposure"]["state"] = "TOTAL_EXPOSURE_GUARD_WARNING"
        result = evaluate_integration(values)
        self.assertEqual(result["decision"], "WARN")

    def test_blocking_guard(self):
        values = normal_results()
        values["kill_switch"]["state"] = "KILL_SWITCH_GUARD_BLOCKED"
        values["kill_switch"]["risk_operations_allowed"] = False
        result = evaluate_integration(values)
        self.assertEqual(result["decision"], "BLOCKED")

    def test_missing_source(self):
        values = normal_results()
        values.pop("drawdown")
        result = evaluate_integration(values)
        self.assertEqual(result["decision"], "BLOCKED")

    def test_stage_mismatch(self):
        values = normal_results()
        values["position"]["stage"] = "WRONG"
        result = evaluate_integration(values)
        self.assertEqual(result["decision"], "BLOCKED")

    def test_policy_hash_mismatch(self):
        values = normal_results()
        values["position"]["policy_hash"] = "b" * 64
        result = evaluate_integration(values)
        self.assertFalse(result["policy_hash_consistent"])

    def test_execution_authorization_still_disabled(self):
        result = run_guard(normal_results())
        self.assertFalse(result["execution_authorization_allowed"])

    def test_zero_orders(self):
        result = run_guard(normal_results())
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
