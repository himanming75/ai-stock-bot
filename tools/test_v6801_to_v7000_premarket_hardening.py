from __future__ import annotations
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from premarket_hardening.cleanup import build_cleanup_plan
from premarket_hardening.etrade_mock import ETradeMockClient
from premarket_hardening.failure_injection import (
    execute_fixture_scenario,
)
from premarket_hardening.monitor import (
    RuntimeSample,
    evaluate_samples,
)
from premarket_hardening.multi_account import (
    fixture_accounts,
    validate_accounts,
)
from premarket_hardening.service import (
    PreMarketHardeningCertificationService,
)


class Tests(unittest.TestCase):
    def test_cleanup_dry_run(self):
        now = datetime.now(timezone.utc)
        result = build_cleanup_plan(
            files=[{
                "path": (
                    "release/x/actual/cycle_0001/a.json"
                ),
                "modified_at": now - timedelta(days=20),
            }],
            now=now,
        )
        self.assertEqual(result["delete_count"], 1)
        self.assertTrue(result["dry_run"])

    def test_monitor(self):
        result = evaluate_samples([
            RuntimeSample(
                "0", 1, Decimal("100"), Decimal("10"),
                Decimal("30"), 0, 0, 1,
            ),
            RuntimeSample(
                "1", 2, Decimal("105"), Decimal("20"),
                Decimal("31"), 0, 0, 2,
            ),
        ])
        self.assertEqual(result["status"], "PASS")

    def test_failure_injection(self):
        result = execute_fixture_scenario(
            "MARKET_DATA_STALE"
        )
        self.assertEqual(
            result["observed_action"],
            "ALL_STOP",
        )

    def test_etrade_mock_write_block(self):
        client = ETradeMockClient()
        with self.assertRaises(PermissionError):
            client.submit_order()

    def test_multi_account_load(self):
        result = validate_accounts(
            fixture_accounts(10)
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["account_count"], 10)

    def test_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                PreMarketHardeningCertificationService()
                .evaluate(output_dir=Path(directory))
            )
            self.assertEqual(result["status"], "PASS")

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                PreMarketHardeningCertificationService()
                .evaluate(output_dir=Path(directory))
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
