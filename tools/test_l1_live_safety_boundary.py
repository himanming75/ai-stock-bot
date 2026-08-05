from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from live_safety.confirmation_gate import evaluate_confirmation
from live_safety.credential_guard import evaluate_credentials
from live_safety.kill_switch import ensure_live_kill_switch
from live_safety.risk_policy import LiveRiskPolicy


class Tests(unittest.TestCase):
    def test_credentials_separated(self):
        result = evaluate_credentials(
            paper_key="paper",
            paper_secret="paper-secret",
            live_key="live",
            live_secret="live-secret",
        )
        self.assertTrue(result["valid"])
        self.assertNotEqual(
            result["paper_key_fingerprint"],
            "paper",
        )
        self.assertNotEqual(
            result["paper_secret_fingerprint"],
            "paper-secret",
        )

    def test_same_credentials_rejected(self):
        result = evaluate_credentials(
            paper_key="same",
            paper_secret="same-secret",
            live_key="same",
            live_secret="same-secret",
        )
        self.assertFalse(result["valid"])

    def test_live_kill_switch_defaults_active(self):
        with tempfile.TemporaryDirectory() as directory:
            result = ensure_live_kill_switch(
                Path(directory) / "kill.json"
            )
        self.assertTrue(result["live_kill_switch_active"])

    def test_risk_policy(self):
        result = LiveRiskPolicy(
            maximum_order_notional=10,
            maximum_daily_orders=1,
            maximum_daily_loss=10,
            maximum_total_exposure=25,
            maximum_position_count=1,
            allowed_symbols=("SPY",),
            allowed_account_ids=(),
        ).evaluate()
        self.assertTrue(result["valid"])

    def test_confirmation_stays_disabled(self):
        result = evaluate_confirmation(
            confirmation_one="",
            confirmation_two="",
            live_network_enabled=False,
            live_write_enabled=False,
        )
        self.assertFalse(result["live_activation_allowed"])
        self.assertTrue(result["valid"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
