from __future__ import annotations

from decimal import Decimal
import json
import unittest

from alpaca_broker import (
    ActualPaperOrderValidator,
    AlpacaConfigurationError,
    AlpacaPaperClient,
    AlpacaPaperConfig,
    OrderValidationPolicy,
    UrllibHttpTransport,
)


class FakeResponse:
    def __init__(self, payload):
        self.raw = json.dumps(payload).encode("utf-8")
        self.status = 200
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


def order(status, filled="0"):
    return {
        "id": "order-1",
        "client_order_id": "BOT-PAPER-ONE-000001",
        "symbol": "AAPL",
        "side": "buy",
        "qty": "1",
        "filled_qty": filled,
        "status": status,
    }


def account():
    return {
        "id": "paper-account",
        "status": "ACTIVE",
        "cash": "950",
        "equity": "1000",
        "buying_power": "1900",
        "trading_blocked": False,
    }


def positions(quantity="1"):
    return [{
        "symbol": "AAPL",
        "qty": quantity,
        "avg_entry_price": "50",
        "market_value": "50",
        "unrealized_pl": "0",
    }]


class ActualAlpacaPaperOrderValidationTests(unittest.TestCase):
    def validator(self, payloads, *, write=False, attempts=5, require_terminal=True):
        opener = QueueOpener(payloads)
        client = AlpacaPaperClient(
            config=AlpacaPaperConfig(
                network_read_enabled=True,
                network_write_enabled=write,
                max_retries=0,
            ),
            api_key="paper-key",
            secret_key="paper-secret",
            transport=UrllibHttpTransport(opener=opener, sleep=lambda _: None),
        )
        validator = ActualPaperOrderValidator(
            client=client,
            policy=OrderValidationPolicy(
                max_poll_attempts=attempts,
                poll_interval_seconds=0,
                require_terminal_status=require_terminal,
            ),
            sleep=lambda _: None,
        )
        return validator, opener

    def test_write_enabled_client_rejected(self):
        client = AlpacaPaperClient(
            config=AlpacaPaperConfig(
                network_read_enabled=True,
                network_write_enabled=True,
            ),
            api_key="key",
            secret_key="secret",
            transport=UrllibHttpTransport(),
        )
        with self.assertRaises(AlpacaConfigurationError):
            ActualPaperOrderValidator(
                client=client,
                policy=OrderValidationPolicy(),
            )

    def test_bad_client_order_id_rejected(self):
        validator, _ = self.validator([])
        with self.assertRaises(AlpacaConfigurationError):
            validator.poll_order("unexpected")

    def test_immediate_fill(self):
        validator, opener = self.validator([order("filled", "1"), account(), positions()])
        report = validator.validate(client_order_id="BOT-PAPER-ONE-000001")
        self.assertTrue(report.terminal_status_reached)
        self.assertEqual(report.poll_attempts, 1)
        self.assertEqual(report.filled_quantity, Decimal("1"))
        self.assertEqual([r.get_method() for r, _ in opener.requests], ["GET", "GET", "GET"])

    def test_poll_until_filled(self):
        validator, _ = self.validator([
            order("accepted"),
            order("partially_filled", "0.5"),
            order("filled", "1"),
            account(),
            positions(),
        ])
        report = validator.validate(client_order_id="BOT-PAPER-ONE-000001")
        self.assertEqual(report.poll_attempts, 3)
        self.assertEqual(report.final_status, "filled")

    def test_rejected_is_terminal(self):
        validator, _ = self.validator([order("rejected"), account(), []])
        report = validator.validate(client_order_id="BOT-PAPER-ONE-000001")
        self.assertEqual(report.final_status, "rejected")
        self.assertEqual(report.position_quantity, Decimal("0"))

    def test_canceled_is_terminal(self):
        validator, _ = self.validator([order("canceled"), account(), []])
        report = validator.validate(client_order_id="BOT-PAPER-ONE-000001")
        self.assertEqual(report.final_status, "canceled")

    def test_nonterminal_raises_after_limit(self):
        validator, _ = self.validator(
            [order("accepted"), order("accepted")],
            attempts=2,
        )
        with self.assertRaises(AlpacaConfigurationError):
            validator.validate(client_order_id="BOT-PAPER-ONE-000001")

    def test_nonterminal_allowed_by_policy(self):
        validator, _ = self.validator(
            [order("accepted"), order("accepted"), account(), []],
            attempts=2,
            require_terminal=False,
        )
        report = validator.validate(client_order_id="BOT-PAPER-ONE-000001")
        self.assertFalse(report.terminal_status_reached)

    def test_read_only_no_writes(self):
        validator, opener = self.validator([order("filled", "1"), account(), positions()])
        report = validator.validate(client_order_id="BOT-PAPER-ONE-000001")
        self.assertEqual(report.write_requests_executed, 0)
        self.assertEqual(report.additional_orders_submitted, 0)
        self.assertNotIn("POST", [r.get_method() for r, _ in opener.requests])

    def test_position_quantity_reported(self):
        validator, _ = self.validator([order("filled", "1"), account(), positions("1")])
        report = validator.validate(client_order_id="BOT-PAPER-ONE-000001")
        self.assertEqual(report.position_quantity, Decimal("1"))

    def test_policy_attempt_limit(self):
        with self.assertRaises(AlpacaConfigurationError):
            OrderValidationPolicy(max_poll_attempts=0).validate()

    def test_policy_interval_limit(self):
        with self.assertRaises(AlpacaConfigurationError):
            OrderValidationPolicy(poll_interval_seconds=31).validate()


if __name__ == "__main__":
    unittest.main()
