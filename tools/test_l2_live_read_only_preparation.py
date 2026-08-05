from __future__ import annotations
import unittest

from live_read.adapter import AlpacaLiveReadAdapter
from live_read.http_guard import (
    GetOnlyHttpGuard,
    LiveReadMethodError,
)
from live_read.service import run_snapshot


def transport(method, path):
    values = {
        "/v2/account": {
            "id": "a", "status": "ACTIVE", "currency": "USD",
            "cash": "1", "buying_power": "1", "equity": "1",
        },
        "/v2/positions": [],
        "/v2/orders?status=open&direction=asc": [],
        "/v2/clock": {"is_open": False},
        "/v2/assets/SPY": {
            "id": "s", "symbol": "SPY", "status": "active",
            "tradable": True,
        },
    }
    return values[path]


class Tests(unittest.TestCase):
    def test_get_only(self):
        guard = GetOnlyHttpGuard(
            network_enabled=False,
            transport=transport,
        )
        self.assertEqual(
            guard.request_json("GET", "/v2/account")["status"],
            "ACTIVE",
        )

    def test_write_rejected(self):
        guard = GetOnlyHttpGuard(
            network_enabled=False,
            transport=transport,
        )
        with self.assertRaises(LiveReadMethodError):
            guard.request_json("POST", "/v2/orders")

    def test_symbol_validation(self):
        adapter = AlpacaLiveReadAdapter(
            GetOnlyHttpGuard(
                network_enabled=False,
                transport=transport,
            )
        )
        with self.assertRaises(ValueError):
            adapter.get_asset("BAD/SYMBOL")

    def test_snapshot(self):
        adapter = AlpacaLiveReadAdapter(
            GetOnlyHttpGuard(
                network_enabled=False,
                transport=transport,
            )
        )
        result = run_snapshot(adapter, ["SPY"], mode="TEST")
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["actual_live_read_performed"])

    def test_zero_orders(self):
        adapter = AlpacaLiveReadAdapter(
            GetOnlyHttpGuard(
                network_enabled=False,
                transport=transport,
            )
        )
        result = run_snapshot(adapter, ["SPY"], mode="TEST")
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
