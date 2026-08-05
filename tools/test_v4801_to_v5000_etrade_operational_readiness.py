from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from multi_broker_etrade_recovery.service import (
    ETradeRecoveryOperationalReadinessService,
)
from multi_broker_etrade_recovery.state_machine import decide_recovery


class Tests(unittest.TestCase):
    def test_token_renew(self):
        decision = decide_recovery("TOKEN_RENEW_REQUIRED")
        self.assertEqual(decision.state, "RENEWING_TOKEN")
        self.assertFalse(decision.write_allowed)

    def test_rate_limit_backoff(self):
        decision = decide_recovery("RATE_LIMIT", 1)
        self.assertEqual(
            decision.retry_after_seconds,
            180,
        )

    def test_account_restriction(self):
        decision = decide_recovery("ACCOUNT_RESTRICTED")
        self.assertEqual(
            decision.state,
            "MANUAL_ACCOUNT_RECOVERY",
        )
        self.assertTrue(decision.requires_operator)

    def test_unknown_failsafe(self):
        decision = decide_recovery("UNCLASSIFIED_FAILURE")
        self.assertEqual(
            decision.state,
            "FAILSAFE_BLOCKED",
        )
        self.assertFalse(decision.read_allowed)

    def test_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            result = ETradeRecoveryOperationalReadinessService().evaluate(
                output_dir=Path(directory)
            )
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(
                result["read_only_platform_code_complete"]
            )
            self.assertFalse(
                result["actual_sandbox_validation_complete"]
            )

    def test_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ETradeRecoveryOperationalReadinessService().evaluate(
                output_dir=root
            )
            self.assertTrue(
                (
                    root
                    / "etrade_final_readiness_dashboard.json"
                ).exists()
            )
            self.assertTrue(
                (
                    root
                    / "etrade_operational_readiness_ledger.jsonl"
                ).exists()
            )

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            result = ETradeRecoveryOperationalReadinessService().evaluate(
                output_dir=Path(directory)
            )
            self.assertFalse(
                result["actual_broker_write_performed"]
            )
            self.assertEqual(
                result["actual_paper_orders_submitted"],
                0,
            )
            self.assertEqual(
                result["actual_live_orders_submitted"],
                0,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
