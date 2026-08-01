from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import unittest

from autonomous_paper_runtime import AutonomousPaperReadSession


@dataclass
class Config:
    base_url: str = "https://paper-api.alpaca.markets"
    network_read_enabled: bool = True
    network_write_enabled: bool = False


@dataclass
class Account:
    account_id: str = "paper-account-123456"
    status: str = "ACTIVE"
    trading_blocked: bool = False
    cash: str = "1000"
    buying_power: str = "2000"
    equity: str = "1100"


@dataclass
class Clock:
    is_open: bool = True
    timestamp: datetime = datetime(2026, 8, 3, 15, 0, tzinfo=timezone.utc)
    next_open: datetime = datetime(2026, 8, 4, 13, 30, tzinfo=timezone.utc)
    next_close: datetime = datetime(2026, 8, 3, 20, 0, tzinfo=timezone.utc)


@dataclass
class Position:
    symbol: str


@dataclass
class Order:
    client_order_id: str


class FakeClient:
    def __init__(self):
        self.config = Config()
        self.network_requests_executed = 0
        self.write_requests_executed = 0
        self.request_methods = []

    def _get(self):
        self.network_requests_executed += 1
        self.request_methods.append("GET")

    def get_account(self):
        self._get()
        return Account()

    def get_clock(self):
        self._get()
        return Clock()

    def list_positions(self):
        self._get()
        return [Position("AAPL"), Position("SPY")]

    def list_orders(self, *, status, limit=None):
        self._get()
        if status == "open":
            return [Order("open-1")]
        return [Order("closed-1"), Order("closed-2")]


class ActualAutonomousPaperReadSessionTests(unittest.TestCase):
    def test_snapshot_counts(self):
        result = AutonomousPaperReadSession(client=FakeClient()).run()
        self.assertEqual(result.position_count, 2)
        self.assertEqual(result.open_order_count, 1)
        self.assertEqual(result.closed_order_count, 2)

    def test_exactly_five_gets(self):
        result = AutonomousPaperReadSession(client=FakeClient()).run()
        self.assertEqual(result.request_methods, ("GET",) * 5)
        self.assertEqual(result.read_request_count, 5)

    def test_account_id_redacted(self):
        result = AutonomousPaperReadSession(client=FakeClient()).run()
        self.assertNotIn("paper-account-123456", result.account_id_redacted)
        self.assertTrue("*" in result.account_id_redacted)

    def test_financial_values(self):
        result = AutonomousPaperReadSession(client=FakeClient()).run()
        self.assertEqual(result.cash, Decimal("1000"))
        self.assertEqual(result.buying_power, Decimal("2000"))
        self.assertEqual(result.equity, Decimal("1100"))

    def test_symbols_sorted(self):
        result = AutonomousPaperReadSession(client=FakeClient()).run()
        self.assertEqual(result.symbols_held, ("AAPL", "SPY"))

    def test_autonomous_read_ready(self):
        result = AutonomousPaperReadSession(client=FakeClient()).run()
        self.assertTrue(result.autonomous_read_ready)

    def test_blocked_account_not_ready(self):
        client = FakeClient()
        client.get_account = lambda: (
            client._get() or Account(trading_blocked=True)
        )
        result = AutonomousPaperReadSession(client=client).run()
        self.assertFalse(result.autonomous_read_ready)

    def test_write_enabled_rejected(self):
        client = FakeClient()
        client.config.network_write_enabled = True
        with self.assertRaises(ValueError):
            AutonomousPaperReadSession(client=client)

    def test_read_disabled_rejected(self):
        client = FakeClient()
        client.config.network_read_enabled = False
        with self.assertRaises(ValueError):
            AutonomousPaperReadSession(client=client)

    def test_live_url_rejected(self):
        client = FakeClient()
        client.config.base_url = "https://api.alpaca.markets"
        with self.assertRaises(ValueError):
            AutonomousPaperReadSession(client=client)

    def test_closed_order_limit_validation(self):
        with self.assertRaises(ValueError):
            AutonomousPaperReadSession(client=FakeClient(), closed_order_limit=0)
        with self.assertRaises(ValueError):
            AutonomousPaperReadSession(client=FakeClient(), closed_order_limit=501)

    def test_non_get_method_rejected(self):
        client = FakeClient()
        original = client.list_orders

        def bad_list_orders(*, status, limit=None):
            value = original(status=status, limit=limit)
            if status == "closed":
                client.request_methods[-1] = "POST"
            return value

        client.list_orders = bad_list_orders
        with self.assertRaises(RuntimeError):
            AutonomousPaperReadSession(client=client).run()

    def test_write_counter_rejected(self):
        client = FakeClient()
        client.write_requests_executed = 1
        with self.assertRaises(RuntimeError):
            AutonomousPaperReadSession(client=client).run()

    def test_order_counters_zero(self):
        result = AutonomousPaperReadSession(client=FakeClient()).run()
        self.assertEqual(result.actual_paper_orders_submitted, 0)
        self.assertEqual(result.live_orders_submitted, 0)

    def test_json_serialization(self):
        raw = AutonomousPaperReadSession(client=FakeClient()).run().to_json_dict()
        self.assertEqual(raw["cash"], "1000")
        self.assertEqual(raw["request_methods"], ["GET"] * 5)


if __name__ == "__main__":
    unittest.main()
