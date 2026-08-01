from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO
import json
import unittest

from alpaca_broker import (
    AlpacaConfigurationError,
    AlpacaNetworkDisabledError,
    AlpacaPaperClient,
    AlpacaPaperConfig,
    BrokerAccount,
    BrokerPortfolioReconciler,
    BrokerPosition,
    CredentialLoader,
    UrllibHttpTransport,
)
from portfolio_engine import PortfolioSnapshot, PositionSnapshot


class FakeResponse:
    def __init__(self, payload, status=200, request_id="REQ-1"):
        self._raw = json.dumps(payload).encode("utf-8") if payload is not None else b""
        self.status = status
        self.headers = {"X-Request-ID": request_id}

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class QueueOpener:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        return FakeResponse(self.payloads.pop(0))


class AlpacaPaperBrokerIntegrationTests(unittest.TestCase):
    def client(self, payloads, *, read=True, write=False):
        opener = QueueOpener(payloads)
        client = AlpacaPaperClient(
            config=AlpacaPaperConfig(
                network_read_enabled=read,
                network_write_enabled=write,
                max_retries=0,
            ),
            api_key="paper-key",
            secret_key="paper-secret",
            transport=UrllibHttpTransport(opener=opener, sleep=lambda _: None),
        )
        return client, opener

    def test_paper_url_allowed(self):
        AlpacaPaperConfig().validate()

    def test_live_url_rejected(self):
        with self.assertRaises(AlpacaConfigurationError):
            AlpacaPaperConfig(base_url="https://api.alpaca.markets").validate()

    def test_write_requires_read(self):
        with self.assertRaises(AlpacaConfigurationError):
            AlpacaPaperConfig(network_write_enabled=True).validate()

    def test_credential_loading(self):
        loader = CredentialLoader()
        key, secret = loader.load({
            "APCA_API_KEY_ID": "abc",
            "APCA_API_SECRET_KEY": "xyz",
        })
        self.assertEqual((key, secret), ("abc", "xyz"))

    def test_credential_redaction(self):
        self.assertEqual(CredentialLoader.redact("abcdefgh"), "ab****gh")

    def test_network_disabled_by_default(self):
        client, _ = self.client([], read=False)
        with self.assertRaises(AlpacaNetworkDisabledError):
            client.get_account()

    def test_get_account(self):
        client, opener = self.client([{
            "id": "acct-1", "status": "ACTIVE", "cash": "1000",
            "equity": "1100", "buying_power": "2000",
            "trading_blocked": False,
        }])
        account = client.get_account()
        self.assertEqual(account.cash, Decimal("1000"))
        self.assertEqual(client.network_requests_executed, 1)
        self.assertIn("/v2/account", opener.requests[0][0].full_url)

    def test_get_clock(self):
        client, _ = self.client([{
            "timestamp": "2026-08-01T16:00:00Z",
            "is_open": True,
            "next_open": "2026-08-02T13:30:00Z",
            "next_close": "2026-08-01T20:00:00Z",
        }])
        clock = client.get_clock()
        self.assertTrue(clock.is_open)
        self.assertIsNotNone(clock.timestamp.tzinfo)

    def test_list_positions(self):
        client, _ = self.client([[{
            "symbol": "AAPL", "qty": "2", "avg_entry_price": "50",
            "market_value": "110", "unrealized_pl": "10",
        }]])
        positions = client.list_positions()
        self.assertEqual(positions[0].quantity, Decimal("2"))

    def test_list_orders(self):
        client, opener = self.client([[{
            "id": "o1", "client_order_id": "c1", "symbol": "AAPL",
            "side": "buy", "qty": "1", "filled_qty": "0", "status": "new",
        }]])
        orders = client.list_orders(status="all", limit=10)
        self.assertEqual(orders[0].status, "new")
        self.assertIn("status=all", opener.requests[0][0].full_url)

    def test_get_order_by_client_id(self):
        client, opener = self.client([{
            "id": "o1", "client_order_id": "c1", "symbol": "AAPL",
            "side": "buy", "qty": "1", "filled_qty": "1", "status": "filled",
        }])
        order = client.get_order_by_client_id("c1")
        self.assertEqual(order.filled_quantity, Decimal("1"))
        self.assertIn("client_order_id=c1", opener.requests[0][0].full_url)

    def test_submit_preview_never_executes(self):
        client, _ = self.client([], read=False)
        preview = client.preview_submit_order({
            "symbol": "AAPL", "qty": "1", "side": "buy",
            "type": "market", "time_in_force": "day",
            "client_order_id": "BOT-1",
        })
        self.assertFalse(preview["network_executed"])
        self.assertEqual(client.network_requests_executed, 0)

    def test_submit_blocked_without_write_opt_in(self):
        client, _ = self.client([], read=True, write=False)
        with self.assertRaises(AlpacaNetworkDisabledError):
            client.submit_order({
                "symbol": "AAPL", "qty": "1", "side": "buy",
                "type": "market", "time_in_force": "day",
                "client_order_id": "BOT-1",
            })

    def test_cancel_blocked_without_write_opt_in(self):
        client, _ = self.client([], read=True, write=False)
        with self.assertRaises(AlpacaNetworkDisabledError):
            client.cancel_order("order-1")

    def test_reconciliation_match(self):
        captured = datetime(2026, 8, 1, 16, tzinfo=timezone.utc)
        internal = PortfolioSnapshot(
            captured_at=captured, cash=Decimal("950"), equity=Decimal("1000"),
            market_value=Decimal("50"), realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("0"), buying_power=Decimal("950"),
            positions=(PositionSnapshot(
                symbol="AAPL", quantity=Decimal("1"), average_price=Decimal("50"),
                market_price=Decimal("50"), market_value=Decimal("50"),
                unrealized_pnl=Decimal("0"), realized_pnl=Decimal("0"),
            ),),
        )
        account = BrokerAccount("acct", "ACTIVE", Decimal("950"), Decimal("1000"), Decimal("950"), False)
        positions = (BrokerPosition("AAPL", Decimal("1"), Decimal("50"), Decimal("50"), Decimal("0")),)
        result = BrokerPortfolioReconciler().reconcile(
            internal=internal, account=account, positions=positions
        )
        self.assertTrue(result.matched)

    def test_reconciliation_detects_quantity_difference(self):
        captured = datetime(2026, 8, 1, 16, tzinfo=timezone.utc)
        internal = PortfolioSnapshot(
            captured_at=captured, cash=Decimal("950"), equity=Decimal("1000"),
            market_value=Decimal("50"), realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("0"), buying_power=Decimal("950"),
            positions=(PositionSnapshot(
                symbol="AAPL", quantity=Decimal("1"), average_price=Decimal("50"),
                market_price=Decimal("50"), market_value=Decimal("50"),
                unrealized_pnl=Decimal("0"), realized_pnl=Decimal("0"),
            ),),
        )
        account = BrokerAccount("acct", "ACTIVE", Decimal("950"), Decimal("1000"), Decimal("950"), False)
        positions = (BrokerPosition("AAPL", Decimal("2"), Decimal("50"), Decimal("100"), Decimal("0")),)
        result = BrokerPortfolioReconciler().reconcile(
            internal=internal, account=account, positions=positions
        )
        self.assertFalse(result.matched)
        self.assertIn("AAPL", result.quantity_mismatches)


if __name__ == "__main__":
    unittest.main()
