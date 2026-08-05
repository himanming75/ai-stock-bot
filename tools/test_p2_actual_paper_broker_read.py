from __future__ import annotations
import unittest

from alpaca_paper_read.config import ReadConfig
from alpaca_paper_read.http_client import ReadOnlyHttpClient
from p2_broker_read.service import _decimal_valid, _fingerprint


class Tests(unittest.TestCase):
    def test_decimal_validation(self):
        self.assertTrue(_decimal_valid("100.50"))
        self.assertFalse(_decimal_valid("-1"))
        self.assertFalse(_decimal_valid("bad"))

    def test_fingerprint_not_plaintext(self):
        value = _fingerprint("account-id")
        self.assertNotEqual(value, "account-id")
        self.assertEqual(len(value), 16)

    def test_read_client_rejects_post(self):
        config = ReadConfig(
            api_key="k",
            secret_key="s",
            base_url="https://paper-api.alpaca.markets",
            timeout_seconds=1,
            maximum_attempts=1,
            backoff_seconds=0,
            actual_network_enabled=True,
        )
        client = ReadOnlyHttpClient(config)
        with self.assertRaises(ValueError):
            client.request_json("POST", "/v2/orders")

    def test_read_client_rejects_network_when_disabled(self):
        config = ReadConfig(
            api_key="k",
            secret_key="s",
            base_url="https://paper-api.alpaca.markets",
            timeout_seconds=1,
            maximum_attempts=1,
            backoff_seconds=0,
            actual_network_enabled=False,
        )
        client = ReadOnlyHttpClient(config)
        with self.assertRaises(Exception):
            client.get_json("/v2/account")

    def test_live_endpoint_not_enforced(self):
        config = ReadConfig(
            api_key="k",
            secret_key="s",
            base_url="https://api.alpaca.markets",
            timeout_seconds=1,
            maximum_attempts=1,
            backoff_seconds=0,
            actual_network_enabled=True,
        )
        self.assertFalse(config.paper_endpoint_enforced)


if __name__ == "__main__":
    unittest.main(verbosity=2)
