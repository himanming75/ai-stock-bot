from __future__ import annotations
from decimal import Decimal
import tempfile
import unittest
from pathlib import Path

from alpaca_paper_read.config import PAPER_BASE_URL
from broker_integration.execution_config import ExecutionConfig
from broker_integration.execution_models import CanonicalOrderRequest
from broker_integration.execution_service import submit_paper_order
from broker_integration.safety_checks import estimated_notional


class FakeHttp:
    def submit_order(self, payload):
        return {"id": "paper-1", "status": "accepted"}, "request-1"


def config():
    return ExecutionConfig(
        api_key="key",
        secret_key="secret",
        base_url=PAPER_BASE_URL,
        network_enabled=True,
        write_enabled=True,
        confirmation="I_UNDERSTAND_THIS_SUBMITS_A_PAPER_ORDER",
        maximum_order_notional=Decimal("10"),
        maximum_daily_orders=3,
        allowed_symbols=frozenset({"AAPL"}),
        timeout_seconds=1,
        maximum_attempts=1,
        backoff_seconds=0,
    )


class Tests(unittest.TestCase):
    def test_notional_market_uses_order_notional(self):
        order = CanonicalOrderRequest(
            "AAPL", "buy", "market", "day",
            notional=Decimal("5"),
            client_order_id="p2a-1",
        )
        value, source = estimated_notional(order, None)
        self.assertEqual(value, Decimal("5"))
        self.assertEqual(source, "ORDER_NOTIONAL")

    def test_limit_uses_qty_times_limit_price(self):
        order = CanonicalOrderRequest(
            "AAPL", "buy", "limit", "day",
            qty=Decimal("2"),
            limit_price=Decimal("7"),
            client_order_id="p2a-2",
        )
        value, source = estimated_notional(order, None)
        self.assertEqual(value, Decimal("14"))
        self.assertEqual(source, "QTY_X_LIMIT_PRICE")

    def test_market_qty_uses_latest_price_and_buffer(self):
        order = CanonicalOrderRequest(
            "AAPL", "buy", "market", "day",
            qty=Decimal("1"),
            client_order_id="p2a-3",
        )
        value, source = estimated_notional(order, Decimal("100"))
        self.assertEqual(value, Decimal("103.00"))
        self.assertEqual(source, "QTY_X_LATEST_TRADE_X_1.03")

    def test_market_qty_requires_latest_price(self):
        order = CanonicalOrderRequest(
            "AAPL", "buy", "market", "day",
            qty=Decimal("1"),
            client_order_id="p2a-4",
        )
        with self.assertRaises(ValueError):
            estimated_notional(order, None)

    def test_limit_cannot_bypass_order_limit(self):
        with tempfile.TemporaryDirectory() as d:
            result = submit_paper_order(
                config=config(),
                order=CanonicalOrderRequest(
                    "AAPL", "buy", "limit", "day",
                    qty=Decimal("1"),
                    limit_price=Decimal("200"),
                    client_order_id="p2a-5",
                ),
                account={
                    "status": "ACTIVE",
                    "account_blocked": False,
                    "trading_blocked": False,
                    "buying_power": "1000",
                },
                asset={"status": "active", "tradable": True},
                clock={"is_open": True},
                kill_switch={"kill_switch_active": False},
                risk_permission=True,
                latest_trade_price=None,
                positions=[],
                registry_path=Path(d)/"registry.json",
                order_ledger_path=Path(d)/"orders.jsonl",
                error_ledger_path=Path(d)/"errors.jsonl",
                http=FakeHttp(),
            )
        self.assertFalse(result["submitted"])
        self.assertIn(
            "notional_within_limit",
            result["pre_submit"]["failed"],
        )

    def test_sell_requires_position(self):
        with tempfile.TemporaryDirectory() as d:
            result = submit_paper_order(
                config=config(),
                order=CanonicalOrderRequest(
                    "AAPL", "sell", "market", "day",
                    qty=Decimal("1"),
                    client_order_id="p2a-6",
                ),
                account={
                    "status": "ACTIVE",
                    "account_blocked": False,
                    "trading_blocked": False,
                    "buying_power": "1000",
                },
                asset={"status": "active", "tradable": True},
                clock={"is_open": True},
                kill_switch={"kill_switch_active": False},
                risk_permission=True,
                latest_trade_price=Decimal("5"),
                positions=[],
                registry_path=Path(d)/"registry.json",
                order_ledger_path=Path(d)/"orders.jsonl",
                error_ledger_path=Path(d)/"errors.jsonl",
                http=FakeHttp(),
            )
        self.assertFalse(result["submitted"])
        self.assertIn(
            "sell_quantity_available",
            result["pre_submit"]["failed"],
        )

    def test_sell_with_position_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            result = submit_paper_order(
                config=config(),
                order=CanonicalOrderRequest(
                    "AAPL", "sell", "market", "day",
                    qty=Decimal("1"),
                    client_order_id="p2a-7",
                ),
                account={
                    "status": "ACTIVE",
                    "account_blocked": False,
                    "trading_blocked": False,
                    "buying_power": "1000",
                },
                asset={"status": "active", "tradable": True},
                clock={"is_open": True},
                kill_switch={"kill_switch_active": False},
                risk_permission=True,
                latest_trade_price=Decimal("5"),
                positions=[{"symbol": "AAPL", "qty": "2"}],
                registry_path=Path(d)/"registry.json",
                order_ledger_path=Path(d)/"orders.jsonl",
                error_ledger_path=Path(d)/"errors.jsonl",
                http=FakeHttp(),
            )
        self.assertTrue(result["submitted"])

    def test_notional_sell_rejected(self):
        with self.assertRaises(ValueError):
            CanonicalOrderRequest(
                "AAPL", "sell", "market", "day",
                notional=Decimal("5"),
                client_order_id="p2a-8",
            ).validate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
