from __future__ import annotations
from decimal import Decimal
import tempfile
import unittest
from pathlib import Path

from broker_integration.p3_accounting import compare_account, compare_positions
from broker_integration.p3_fill_registry import register_fill
from broker_integration.p3_service import run_p3_sync


class Tests(unittest.TestCase):
    def test_fill_registry_blocks_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fills.json"
            order = {
                "id": "order-1",
                "client_order_id": "client-1",
                "symbol": "AAPL",
                "side": "buy",
                "filled_qty": "1",
                "filled_avg_price": "100",
                "filled_at": "2026-08-05T14:00:00Z",
            }
            created1, key1 = register_fill(path, order)
            created2, key2 = register_fill(path, order)
            self.assertTrue(created1)
            self.assertFalse(created2)
            self.assertEqual(key1, key2)

    def test_position_drift_detected(self):
        drifts = compare_positions(
            [{"symbol": "AAPL", "qty": "2"}],
            [{"symbol": "AAPL", "qty": "1"}],
            Decimal("0.000001"),
        )
        self.assertEqual(len(drifts), 1)

    def test_account_drift_detected(self):
        drifts = compare_account(
            {"cash": "100", "equity": "200"},
            {"cash": "90", "equity": "200"},
            Decimal("1"),
        )
        self.assertEqual(len(drifts), 1)

    def test_healthy_sync_allows_new_orders(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = run_p3_sync(
                broker_account={"cash": "1000", "equity": "1000"},
                broker_positions=[],
                broker_orders=[],
                local_portfolio={"cash": "1000", "equity": "1000"},
                local_positions=[],
                fill_registry_path=base/"registry.json",
                fill_ledger_path=base/"fills.jsonl",
                order_state_ledger_path=base/"orders.jsonl",
                drift_ledger_path=base/"drifts.jsonl",
                latest_result_path=base/"result.json",
            )
        self.assertTrue(result["reconciliation_passed"])
        self.assertTrue(result["new_order_submission_allowed"])

    def test_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = run_p3_sync(
                broker_account={"cash": "1000", "equity": "1000"},
                broker_positions=[{"symbol": "AAPL", "qty": "2"}],
                broker_orders=[],
                local_portfolio={"cash": "1000", "equity": "1000"},
                local_positions=[{"symbol": "AAPL", "qty": "1"}],
                fill_registry_path=base/"registry.json",
                fill_ledger_path=base/"fills.jsonl",
                order_state_ledger_path=base/"orders.jsonl",
                drift_ledger_path=base/"drifts.jsonl",
                latest_result_path=base/"result.json",
            )
        self.assertFalse(result["reconciliation_passed"])
        self.assertTrue(result["fail_closed"])
        self.assertFalse(result["new_order_submission_allowed"])

    def test_partial_fill_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = run_p3_sync(
                broker_account={"cash": "1000", "equity": "1000"},
                broker_positions=[],
                broker_orders=[{
                    "id": "order-1",
                    "client_order_id": "client-1",
                    "symbol": "AAPL",
                    "side": "buy",
                    "status": "partially_filled",
                    "qty": "2",
                    "filled_qty": "1",
                    "filled_avg_price": "100",
                    "submitted_at": "x",
                    "filled_at": "y",
                }],
                local_portfolio={"cash": "1000", "equity": "1000"},
                local_positions=[],
                fill_registry_path=base/"registry.json",
                fill_ledger_path=base/"fills.jsonl",
                order_state_ledger_path=base/"orders.jsonl",
                drift_ledger_path=base/"drifts.jsonl",
                latest_result_path=base/"result.json",
            )
        self.assertEqual(result["new_fill_count"], 1)

    def test_unknown_state_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = run_p3_sync(
                broker_account={"cash": "1000", "equity": "1000"},
                broker_positions=[],
                broker_orders=[{
                    "id": "order-1",
                    "client_order_id": "client-1",
                    "symbol": "AAPL",
                    "side": "buy",
                    "status": "mystery",
                    "qty": "1",
                    "filled_qty": "0",
                }],
                local_portfolio={"cash": "1000", "equity": "1000"},
                local_positions=[],
                fill_registry_path=base/"registry.json",
                fill_ledger_path=base/"fills.jsonl",
                order_state_ledger_path=base/"orders.jsonl",
                drift_ledger_path=base/"drifts.jsonl",
                latest_result_path=base/"result.json",
            )
        self.assertFalse(result["reconciliation_passed"])
        self.assertIn("mystery", result["unknown_order_states"])

    def test_zero_order_design(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = run_p3_sync(
                broker_account={"cash": "1", "equity": "1"},
                broker_positions=[],
                broker_orders=[],
                local_portfolio={"cash": "1", "equity": "1"},
                local_positions=[],
                fill_registry_path=base/"registry.json",
                fill_ledger_path=base/"fills.jsonl",
                order_state_ledger_path=base/"orders.jsonl",
                drift_ledger_path=base/"drifts.jsonl",
                latest_result_path=base/"result.json",
            )
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
