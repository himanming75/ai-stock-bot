from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
import unittest

from alpaca_broker import (
    AlpacaConfigurationError,
    ControlledPaperReadValidator,
    READ_CONFIRMATION_ENV,
    READ_CONFIRMATION_TEXT,
    READ_OPT_IN_ENV,
    UrllibHttpTransport,
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


def fixture_payloads():
    return [
        {
            "id": "paper-account-123456",
            "status": "ACTIVE",
            "cash": "1000",
            "equity": "1000",
            "buying_power": "2000",
            "trading_blocked": False,
        },
        {
            "timestamp": "2026-08-01T19:00:00Z",
            "is_open": True,
            "next_open": "2026-08-03T13:30:00Z",
            "next_close": "2026-08-01T20:00:00Z",
        },
        [
            {
                "symbol": "AAPL",
                "qty": "1",
                "avg_entry_price": "50",
                "market_value": "50",
                "unrealized_pl": "0",
            }
        ],
        [
            {
                "id": "open-1",
                "client_order_id": "BOT-OPEN-1",
                "symbol": "AAPL",
                "side": "buy",
                "qty": "1",
                "filled_qty": "0",
                "status": "new",
            }
        ],
        [
            {
                "id": "closed-1",
                "client_order_id": "BOT-CLOSED-1",
                "symbol": "AAPL",
                "side": "buy",
                "qty": "1",
                "filled_qty": "1",
                "status": "filled",
            }
        ],
    ]


class ControlledAlpacaPaperReadTests(unittest.TestCase):
    def env(self):
        return {
            READ_OPT_IN_ENV: "YES",
            READ_CONFIRMATION_ENV: READ_CONFIRMATION_TEXT,
            "APCA_API_KEY_ID": "paper-key",
            "APCA_API_SECRET_KEY": "paper-secret",
        }

    def test_opt_in_required(self):
        with self.assertRaises(AlpacaConfigurationError):
            ControlledPaperReadValidator.validate_opt_in({})

    def test_confirmation_required(self):
        with self.assertRaises(AlpacaConfigurationError):
            ControlledPaperReadValidator.validate_opt_in({
                READ_OPT_IN_ENV: "YES",
                READ_CONFIRMATION_ENV: "wrong",
            })

    def test_factory_enables_read_only(self):
        opener = QueueOpener(fixture_payloads())
        validator = ControlledPaperReadValidator.from_environment(
            self.env(),
            transport=UrllibHttpTransport(opener=opener, sleep=lambda _: None),
        )
        self.assertTrue(validator.client.config.network_read_enabled)
        self.assertFalse(validator.client.config.network_write_enabled)

    def test_controlled_read_calls_five_endpoints(self):
        opener = QueueOpener(fixture_payloads())
        validator = ControlledPaperReadValidator.from_environment(
            self.env(),
            transport=UrllibHttpTransport(opener=opener, sleep=lambda _: None),
        )
        report = validator.run()
        self.assertEqual(report.network_requests_executed, 5)
        self.assertEqual(report.write_requests_executed, 0)
        self.assertEqual(len(opener.requests), 5)

    def test_report_counts(self):
        opener = QueueOpener(fixture_payloads())
        validator = ControlledPaperReadValidator.from_environment(
            self.env(),
            transport=UrllibHttpTransport(opener=opener, sleep=lambda _: None),
        )
        report = validator.run()
        self.assertEqual(report.position_count, 1)
        self.assertEqual(report.open_order_count, 1)
        self.assertEqual(report.closed_order_count, 1)

    def test_account_id_is_redacted(self):
        opener = QueueOpener(fixture_payloads())
        validator = ControlledPaperReadValidator.from_environment(
            self.env(),
            transport=UrllibHttpTransport(opener=opener, sleep=lambda _: None),
        )
        report = validator.run()
        self.assertNotEqual(report.account_id_redacted, "paper-account-123456")
        self.assertIn("*", report.account_id_redacted)

    def test_no_order_submission(self):
        opener = QueueOpener(fixture_payloads())
        validator = ControlledPaperReadValidator.from_environment(
            self.env(),
            transport=UrllibHttpTransport(opener=opener, sleep=lambda _: None),
        )
        report = validator.run()
        self.assertEqual(report.actual_paper_orders_submitted, 0)
        self.assertEqual(report.live_orders_submitted, 0)

    def test_json_serialization(self):
        opener = QueueOpener(fixture_payloads())
        validator = ControlledPaperReadValidator.from_environment(
            self.env(),
            transport=UrllibHttpTransport(opener=opener, sleep=lambda _: None),
        )
        encoded = json.dumps(validator.run().to_json_dict())
        self.assertIn('"cash": "1000"', encoded)

    def test_closed_order_limit_validation(self):
        opener = QueueOpener(fixture_payloads())
        validator = ControlledPaperReadValidator.from_environment(
            self.env(),
            transport=UrllibHttpTransport(opener=opener, sleep=lambda _: None),
        )
        with self.assertRaises(ValueError):
            validator.run(closed_order_limit=0)

    def test_only_get_requests_are_used(self):
        opener = QueueOpener(fixture_payloads())
        validator = ControlledPaperReadValidator.from_environment(
            self.env(),
            transport=UrllibHttpTransport(opener=opener, sleep=lambda _: None),
        )
        validator.run()
        methods = [request.get_method() for request, _ in opener.requests]
        self.assertEqual(methods, ["GET"] * 5)


if __name__ == "__main__":
    unittest.main()
