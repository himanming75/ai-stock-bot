from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

from autonomous_risk_governor.policy_loader import load_and_validate
from autonomous_risk_governor.validation import validate


def policy():
    return {
        "stage": "V391.01A",
        "mode": "RISK_GOVERNOR_POLICY_ONLY",
        "risk_governor_enabled": True,
        "paper_endpoint_only": True,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "daily_loss_limit_pct": 0.02,
        "maximum_drawdown_pct": 0.10,
        "maximum_position_pct": 0.10,
        "maximum_total_exposure_pct": 0.50,
        "maximum_symbol_exposure_pct": 0.10,
        "maximum_consecutive_losses": 5,
        "kill_switch_required": True,
        "kill_switch_active": False,
        "manual_resume_required": True,
        "automatic_resume_enabled": False,
        "risk_operations_allowed": True,
    }


class Tests(unittest.TestCase):
    def test_valid_policy(self):
        self.assertTrue(validate(policy())["valid"])

    def test_live_submission_rejected(self):
        value = policy()
        value["live_submission_enabled"] = True
        self.assertFalse(validate(value)["valid"])

    def test_large_daily_loss_rejected(self):
        value = policy()
        value["daily_loss_limit_pct"] = 0.20
        self.assertFalse(validate(value)["valid"])

    def test_missing_key_rejected(self):
        value = policy()
        value.pop("kill_switch_required")
        self.assertFalse(validate(value)["valid"])

    def test_symbol_limit_rejected(self):
        value = policy()
        value["maximum_symbol_exposure_pct"] = 0.20
        self.assertFalse(validate(value)["valid"])

    def test_kill_switch_blocks_operations(self):
        value = policy()
        value["kill_switch_active"] = True
        value["risk_operations_allowed"] = True
        self.assertFalse(validate(value)["valid"])

    def test_loader_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(policy()), encoding="utf-8")
            result = load_and_validate(path)
            self.assertEqual(len(result["policy_hash"]), 64)
            self.assertEqual(result["state"], "RISK_POLICY_READY")

    def test_zero_orders(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            path.write_text(json.dumps(policy()), encoding="utf-8")
            result = load_and_validate(path)
            self.assertEqual(result["actual_paper_orders_submitted"], 0)
            self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
