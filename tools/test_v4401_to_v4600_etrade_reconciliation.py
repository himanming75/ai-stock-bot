from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from multi_broker_etrade_reconciliation.fixtures import CURRENT, PREVIOUS
from multi_broker_etrade_reconciliation.integrity import validate_snapshot
from multi_broker_etrade_reconciliation.service import (
    ETradePortfolioReconciliationService,
)


class Tests(unittest.TestCase):
    def test_integrity(self):
        self.assertTrue(validate_snapshot(PREVIOUS)["passed"])
        self.assertTrue(validate_snapshot(CURRENT)["passed"])

    def test_change_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            result = ETradePortfolioReconciliationService().evaluate(
                output_dir=Path(directory)
            )
            self.assertEqual(result["status"], "PASS")
            self.assertGreater(result["change_count"], 0)

    def test_order_status_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            result = ETradePortfolioReconciliationService().evaluate(
                output_dir=Path(directory)
            )
            self.assertEqual(
                result["order_status_changes_detected"],
                2,
            )

    def test_position_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            result = ETradePortfolioReconciliationService().evaluate(
                output_dir=Path(directory)
            )
            self.assertEqual(
                result["new_positions_detected"],
                1,
            )
            self.assertEqual(
                result["closed_positions_detected"],
                1,
            )

    def test_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ETradePortfolioReconciliationService().evaluate(
                output_dir=root
            )
            self.assertTrue(
                (root / "etrade_change_events.csv").exists()
            )
            self.assertTrue(
                (root / "etrade_reconciliation_ledger.jsonl").exists()
            )

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            result = ETradePortfolioReconciliationService().evaluate(
                output_dir=Path(directory)
            )
            self.assertFalse(result["actual_broker_write_performed"])
            self.assertEqual(result["actual_paper_orders_submitted"], 0)
            self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
