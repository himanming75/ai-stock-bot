from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from portfolio_sync_recovery.drift import compare_accounts, compare_positions
from portfolio_sync_recovery.engine import run


def policy():
    return {
        "account_drift_tolerance": "1.00",
        "position_qty_tolerance": "0.000001",
        "maximum_account_drift_events": 4,
        "maximum_position_drift_events": 10,
        "maximum_open_orders": 5,
    }


class FakeClient:
    def get_account(self):
        return {
            "status": "ACTIVE",
            "cash": "500",
            "equity": "1500",
            "last_equity": "1490",
            "portfolio_value": "1500",
            "buying_power": "2000",
            "account_blocked": False,
            "trading_blocked": False,
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

    def get_orders(self, status="open"):
        return []


class Tests(unittest.TestCase):
    def test_default_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            result = run(Path(d), policy(), allow_network=False)
            self.assertEqual(result["state"], "PORTFOLIO_SYNC_READY_BLOCKED")

    def test_active_with_fake_client(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {
            "ALPACA_PAPER_API_KEY": "key",
            "ALPACA_PAPER_SECRET_KEY": "secret",
        }):
            result = run(Path(d), policy(), allow_network=True, client=FakeClient())
            self.assertEqual(result["state"], "PORTFOLIO_SYNC_ACTIVE")

    def test_account_drift(self):
        result = compare_accounts(
            {"cash": "100", "equity": "1000", "portfolio_value": "1000", "buying_power": "2000"},
            {"cash": "120", "equity": "1020", "portfolio_value": "1020", "buying_power": "2020"},
            tolerance=__import__("decimal").Decimal("1"),
        )
        self.assertGreaterEqual(len(result), 1)

    def test_position_discovered(self):
        result = compare_positions([], [{"symbol": "SPY", "qty": "1"}], __import__("decimal").Decimal("0.000001"))
        self.assertEqual(result[0]["type"], "POSITION_DISCOVERED")

    def test_position_missing(self):
        result = compare_positions([{"symbol": "SPY", "qty": "1"}], [], __import__("decimal").Decimal("0.000001"))
        self.assertEqual(result[0]["type"], "POSITION_MISSING")

    def test_position_qty_drift(self):
        result = compare_positions(
            [{"symbol": "SPY", "qty": "1"}],
            [{"symbol": "SPY", "qty": "2"}],
            __import__("decimal").Decimal("0.000001"),
        )
        self.assertEqual(result[0]["type"], "POSITION_QTY_DRIFT")

    def test_zero_orders(self):
        with tempfile.TemporaryDirectory() as d:
            result = run(Path(d), policy(), allow_network=False)
            self.assertEqual(result["actual_paper_orders_submitted"], 0)
            self.assertEqual(result["actual_live_orders_submitted"], 0)

    def test_recovery_execution_disabled(self):
        with tempfile.TemporaryDirectory() as d:
            result = run(Path(d), policy(), allow_network=False)
            self.assertFalse(result["automatic_recovery_execution_enabled"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
