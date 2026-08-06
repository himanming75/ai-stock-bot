from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from broker_sync.service import (
    BrokerSyncCertificationService,
)
from broker_sync.sync_engine import BrokerSyncEngine


class Tests(unittest.TestCase):
    def test_certification(self):
        with tempfile.TemporaryDirectory() as d:
            result = (
                BrokerSyncCertificationService()
                .evaluate(output_dir=Path(d))
            )
            self.assertEqual(
                result["status"],
                "PASS",
            )
            self.assertTrue(
                result["partial_success_ready"]
            )

    def test_write_block(self):
        engine = BrokerSyncEngine()
        with self.assertRaises(PermissionError):
            engine.submit_order()
        with self.assertRaises(PermissionError):
            engine.cancel_order()

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as d:
            result = (
                BrokerSyncCertificationService()
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
