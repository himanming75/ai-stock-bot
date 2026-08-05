from __future__ import annotations
import io
import json
import os
import unittest
import urllib.error
from unittest.mock import patch

from alpaca_paper_read.adapter import AlpacaPaperReadAdapter
from alpaca_paper_read.config import PAPER_BASE_URL, ReadConfig, load_config
from alpaca_paper_read.errors import (
    AlpacaAuthenticationError,
    AlpacaNetworkError,
    AlpacaRateLimitError,
)
from alpaca_paper_read.fixture_adapter import FixtureReadAdapter
from alpaca_paper_read.http_client import ReadOnlyHttpClient
from alpaca_paper_read.service import run_read_snapshot


def fixture():
    return {
        "account": {
            "id": "paper-account",
            "status": "ACTIVE",
            "currency": "USD",
            "cash": "50000",
            "portfolio_value": "100000",
            "equity": "100000",
            "buying_power": "200000",
            "trading_blocked": False,
            "account_blocked": False,
            "pattern_day_trader": False,
        },
        "positions": [],
        "open_orders": [],
        "clock": {
            "timestamp": "2026-08-05T10:00:00-04:00",
            "is_open": True,
            "next_open": "2026-08-06T09:30:00-04:00",
            "next_close": "2026-08-05T16:00:00-04:00",
        },
        "assets": {
            "AAPL": {
                "id": "asset-aapl",
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "exchange": "NASDAQ",
                "asset_class": "us_equity",
                "status": "active",
                "tradable": True,
                "marginable": True,
                "shortable": True,
                "easy_to_borrow": True,
                "fractionable": True,
            }
        },
    }


class FakeResponse:
    def __init__(self, value):
        self.value = value
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self):
        return json.dumps(self.value).encode("utf-8")


class Tests(unittest.TestCase):
    def test_fixture_snapshot(self):
        result = run_read_snapshot(
            FixtureReadAdapter(fixture()),
            ["AAPL"],
            "OFFLINE_FIXTURE_READ_ONLY",
        )
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["read_only_http_enforced"])

    def test_live_endpoint_rejected(self):
        with patch.dict(
            os.environ,
            {"APCA_API_BASE_URL": "https://api.alpaca.markets"},
            clear=True,
        ):
            with self.assertRaises(ValueError):
                load_config()

    def test_write_method_rejected(self):
        config = ReadConfig(
            api_key="x",
            secret_key="y",
            base_url=PAPER_BASE_URL,
            timeout_seconds=1,
            maximum_attempts=1,
            backoff_seconds=0,
            actual_network_enabled=True,
        )
        client = ReadOnlyHttpClient(config)
        with self.assertRaises(ValueError):
            client.request_json("POST", "/v2/orders")

    def test_network_opt_in_required(self):
        config = ReadConfig(
            api_key="x",
            secret_key="y",
            base_url=PAPER_BASE_URL,
            timeout_seconds=1,
            maximum_attempts=1,
            backoff_seconds=0,
            actual_network_enabled=False,
        )
        with self.assertRaises(AlpacaNetworkError):
            ReadOnlyHttpClient(config).get_json("/v2/account")

    def test_credentials_required(self):
        config = ReadConfig(
            api_key="",
            secret_key="",
            base_url=PAPER_BASE_URL,
            timeout_seconds=1,
            maximum_attempts=1,
            backoff_seconds=0,
            actual_network_enabled=True,
        )
        with self.assertRaises(AlpacaAuthenticationError):
            ReadOnlyHttpClient(config).get_json("/v2/account")

    def test_successful_get(self):
        config = ReadConfig(
            api_key="x",
            secret_key="y",
            base_url=PAPER_BASE_URL,
            timeout_seconds=1,
            maximum_attempts=1,
            backoff_seconds=0,
            actual_network_enabled=True,
        )
        client = ReadOnlyHttpClient(
            config,
            opener=lambda *a, **k: FakeResponse({"status": "ACTIVE"}),
        )
        self.assertEqual(client.get_json("/v2/account")["status"], "ACTIVE")

    def test_rate_limit_retry_exhausted(self):
        config = ReadConfig(
            api_key="x",
            secret_key="y",
            base_url=PAPER_BASE_URL,
            timeout_seconds=1,
            maximum_attempts=2,
            backoff_seconds=0,
            actual_network_enabled=True,
        )
        def opener(*args, **kwargs):
            raise urllib.error.HTTPError(
                "u", 429, "rate", {}, io.BytesIO(b"")
            )
        client = ReadOnlyHttpClient(config, sleep=lambda _: None, opener=opener)
        with self.assertRaises(AlpacaRateLimitError):
            client.get_json("/v2/account")

    def test_asset_symbol_validation(self):
        config = ReadConfig(
            api_key="x",
            secret_key="y",
            base_url=PAPER_BASE_URL,
            timeout_seconds=1,
            maximum_attempts=1,
            backoff_seconds=0,
            actual_network_enabled=True,
        )
        adapter = AlpacaPaperReadAdapter(
            ReadOnlyHttpClient(
                config,
                opener=lambda *a, **k: FakeResponse({}),
            )
        )
        with self.assertRaises(ValueError):
            adapter.get_asset("../bad")

    def test_zero_orders(self):
        result = run_read_snapshot(
            FixtureReadAdapter(fixture()),
            ["AAPL"],
            "OFFLINE_FIXTURE_READ_ONLY",
        )
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)
        self.assertFalse(result["broker_write_enabled"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
