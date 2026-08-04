from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from paper_execution_lifecycle.engine import run
from paper_execution_lifecycle.lifecycle import build_events
from paper_execution_lifecycle.reconciliation import reconcile_account, reconcile_positions


class FakeClient:
    def get_account(self):
        return {
            "status": "ACTIVE",
            "equity": "1001",
            "cash": "1",
        }

    def get_positions(self):
        return [{
            "symbol": "SPY",
            "qty": "1",
            "avg_entry_price": "1000",
            "market_value": "1000",
            "cost_basis": "1000",
            "unrealized_pl": "0",
            "side": "long",
        }]

    def get_orders(self, status="all"):
        return [{
            "id": "1",
            "client_order_id": "cid-1",
            "symbol": "SPY",
            "side": "buy",
            "type": "market",
            "time_in_force": "day",
            "status": "filled",
            "qty": "1",
            "notional": None,
            "filled_qty": "1",
            "filled_avg_price": "1000",
            "submitted_at": "2026-08-04T10:00:00Z",
            "filled_at": "2026-08-04T10:00:01Z",
        }]


class Tests(unittest.TestCase):
    def test_default_blocked_zero_orders(self):
        with tempfile.TemporaryDirectory() as d:
            result = run(Path(d), allow_network=False)
            self.assertEqual(result["state"], "PAPER_EXECUTION_LIFECYCLE_READY_BLOCKED")
            self.assertEqual(result["actual_paper_orders_submitted"], 0)

    def test_active_with_fake_client(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {
            "ALPACA_PAPER_API_KEY": "key",
            "ALPACA_PAPER_SECRET_KEY": "secret",
        }):
            result = run(Path(d), allow_network=True, client=FakeClient())
            self.assertEqual(result["state"], "PAPER_EXECUTION_LIFECYCLE_ACTIVE")
            self.assertEqual(result["summary"]["filled_orders"], 1)

    def test_order_discovered(self):
        events = build_events([], [{"id": "1", "status": "new", "symbol": "SPY"}])
        self.assertEqual(events[0]["type"], "ORDER_DISCOVERED")

    def test_status_change(self):
        events = build_events(
            [{"id": "1", "status": "new", "filled_qty": "0", "filled_avg_price": None}],
            [{"id": "1", "status": "filled", "filled_qty": "1", "filled_avg_price": "100"}],
        )
        kinds = {item["type"] for item in events}
        self.assertIn("ORDER_STATUS_CHANGED", kinds)
        self.assertIn("FILLED_QTY_CHANGED", kinds)

    def test_position_reconciliation_match(self):
        result = reconcile_positions(
            [{"symbol": "SPY", "side": "buy", "status": "filled", "filled_qty": "1"}],
            [{"symbol": "SPY", "qty": "1"}],
        )
        self.assertTrue(result["matched"])

    def test_position_reconciliation_difference(self):
        result = reconcile_positions(
            [{"symbol": "SPY", "side": "buy", "status": "filled", "filled_qty": "1"}],
            [{"symbol": "SPY", "qty": "2"}],
        )
        self.assertFalse(result["matched"])

    def test_account_reconciliation(self):
        result = reconcile_account(
            {"equity": "1001", "cash": "1"},
            [{"market_value": "1000"}],
        )
        self.assertTrue(result["within_tolerance"])

    def test_live_orders_always_zero(self):
        with tempfile.TemporaryDirectory() as d:
            result = run(Path(d), allow_network=False)
            self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
