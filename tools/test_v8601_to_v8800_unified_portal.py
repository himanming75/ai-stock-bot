from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from unified_trading_portal.data import (
    load_portal_snapshot,
)
from unified_trading_portal.service import (
    UnifiedPortalCertificationService,
)


class Tests(unittest.TestCase):
    def test_missing_snapshot_safe(self):
        with tempfile.TemporaryDirectory() as d:
            value = load_portal_snapshot(
                Path(d) / "missing.json"
            )
            self.assertEqual(
                value["overall_status"],
                "NO_DATA",
            )
            self.assertFalse(
                value["broker_write_enabled"]
            )

    def test_certification(self):
        with tempfile.TemporaryDirectory() as d:
            result = (
                UnifiedPortalCertificationService()
                .evaluate(output_dir=Path(d))
            )
            self.assertEqual(
                result["status"],
                "PASS",
            )
            self.assertEqual(
                result["account_count"],
                2,
            )

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as d:
            result = (
                UnifiedPortalCertificationService()
                .evaluate(output_dir=Path(d))
            )
            self.assertFalse(
                result[
                    "actual_broker_write_performed"
                ]
            )
            self.assertEqual(
                result[
                    "actual_paper_orders_submitted"
                ],
                0,
            )
            self.assertEqual(
                result[
                    "actual_live_orders_submitted"
                ],
                0,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
