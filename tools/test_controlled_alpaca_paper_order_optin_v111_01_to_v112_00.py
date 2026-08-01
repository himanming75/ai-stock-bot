from __future__ import annotations

from decimal import Decimal
import json
import unittest

from alpaca_broker import (
    AlpacaConfigurationError,
    ControlledPaperOrderOptIn,
    UrllibHttpTransport,
    WRITE_CONFIRMATION_ENV,
    WRITE_CONFIRMATION_TEXT,
    WRITE_OPT_IN_ENV,
)


class FakeResponse:
    def __init__(self, payload, status=200):
        self.raw = json.dumps(payload).encode("utf-8")
        self.status = status
        self.headers = {"X-Request-ID": "fixture-request"}

    def read(self):
        return self.raw

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


def submission_payloads():
    return [
        {
            "id": "paper-account",
            "status": "ACTIVE",
            "cash": "1000",
            "equity": "1000",
            "buying_power": "2000",
            "trading_blocked": False,
        },
        {
            "timestamp": "2026-08-03T15:00:00Z",
            "is_open": True,
            "next_open": "2026-08-04T13:30:00Z",
            "next_close": "2026-08-03T20:00:00Z",
        },
        [],
        [],
        {
            "id": "order-1",
            "client_order_id": "BOT-PAPER-ONE-000001",
            "symbol": "AAPL",
            "side": "buy",
            "qty": "1",
            "filled_qty": "0",
            "status": "accepted",
        },
    ]


class ControlledPaperOrderOptInTests(unittest.TestCase):
    def env(self):
        return {
            WRITE_OPT_IN_ENV: "YES",
            WRITE_CONFIRMATION_ENV: WRITE_CONFIRMATION_TEXT,
            "APCA_API_KEY_ID": "paper-key",
            "APCA_API_SECRET_KEY": "paper-secret",
        }

    def optin(self, payloads=None):
        opener = QueueOpener(payloads or [])
        optin = ControlledPaperOrderOptIn.from_environment(
            self.env(),
            transport=UrllibHttpTransport(opener=opener, sleep=lambda _: None),
        )
        return optin, opener

    def plan(self, **overrides):
        values = {
            "symbol": "AAPL",
            "side": "buy",
            "quantity": Decimal("1"),
            "reference_price": Decimal("50"),
            "client_order_id": "BOT-PAPER-ONE-000001",
        }
        values.update(overrides)
        return ControlledPaperOrderOptIn.build_plan(**values)

    def test_opt_in_required(self):
        with self.assertRaises(AlpacaConfigurationError):
            ControlledPaperOrderOptIn.validate_opt_in({})

    def test_exact_confirmation_required(self):
        with self.assertRaises(AlpacaConfigurationError):
            ControlledPaperOrderOptIn.validate_opt_in({
                WRITE_OPT_IN_ENV: "YES",
                WRITE_CONFIRMATION_ENV: "wrong",
            })

    def test_allowlist(self):
        with self.assertRaises(AlpacaConfigurationError):
            self.plan(symbol="TSLA")

    def test_quantity_limit(self):
        with self.assertRaises(AlpacaConfigurationError):
            self.plan(quantity=Decimal("2"))

    def test_notional_limit(self):
        with self.assertRaises(AlpacaConfigurationError):
            self.plan(reference_price=Decimal("101"))

    def test_preview_is_network_free(self):
        optin, opener = self.optin()
        report = optin.preview(self.plan())
        self.assertFalse(report.submitted)
        self.assertEqual(report.network_requests_executed, 0)
        self.assertEqual(report.actual_paper_orders_submitted, 0)
        self.assertEqual(opener.requests, [])

    def test_submit_once_uses_four_reads_one_write(self):
        optin, opener = self.optin(submission_payloads())
        report = optin.submit_once(self.plan())
        self.assertTrue(report.submitted)
        self.assertEqual(report.actual_paper_orders_submitted, 1)
        self.assertEqual(report.network_requests_executed, 5)
        self.assertEqual(report.write_requests_executed, 1)
        self.assertEqual([r.get_method() for r, _ in opener.requests], [
            "GET", "GET", "GET", "GET", "POST"
        ])

    def test_single_use_consumption(self):
        optin, _ = self.optin(submission_payloads())
        optin.submit_once(self.plan())
        with self.assertRaises(AlpacaConfigurationError):
            optin.submit_once(self.plan())

    def test_market_closed_blocks_before_write(self):
        payloads = submission_payloads()
        payloads[1]["is_open"] = False
        optin, opener = self.optin(payloads)
        with self.assertRaises(AlpacaConfigurationError):
            optin.submit_once(self.plan())
        self.assertEqual([r.get_method() for r, _ in opener.requests], ["GET", "GET"])

    def test_existing_open_order_blocks(self):
        payloads = submission_payloads()
        payloads[2] = [{
            "id": "existing", "client_order_id": "existing", "symbol": "SPY",
            "side": "buy", "qty": "1", "filled_qty": "0", "status": "new",
        }]
        optin, opener = self.optin(payloads)
        with self.assertRaises(AlpacaConfigurationError):
            optin.submit_once(self.plan())
        self.assertEqual([r.get_method() for r, _ in opener.requests], ["GET", "GET", "GET"])

    def test_existing_position_blocks_buy(self):
        payloads = submission_payloads()
        payloads[3] = [{
            "symbol": "AAPL", "qty": "1", "avg_entry_price": "50",
            "market_value": "50", "unrealized_pl": "0",
        }]
        optin, opener = self.optin(payloads)
        with self.assertRaises(AlpacaConfigurationError):
            optin.submit_once(self.plan())
        self.assertNotIn("POST", [r.get_method() for r, _ in opener.requests])

    def test_trading_blocked_account(self):
        payloads = submission_payloads()
        payloads[0]["trading_blocked"] = True
        optin, opener = self.optin(payloads)
        with self.assertRaises(AlpacaConfigurationError):
            optin.submit_once(self.plan())
        self.assertEqual(len(opener.requests), 1)


if __name__ == "__main__":
    unittest.main()
