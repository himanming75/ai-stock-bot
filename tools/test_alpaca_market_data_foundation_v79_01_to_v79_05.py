import json
import tempfile
import unittest
from pathlib import Path

from alpaca_market_data import (
    BarRequest,
    MarketBar,
    OfflineAlpacaMarketDataAdapter,
    build_foundation_certificate,
    inspect_alpaca_installation,
    load_safety_config,
)

class AlpacaMarketDataFoundationTests(unittest.TestCase):
    def test_v79_01_install_contract_never_runs_network(self):
        status = inspect_alpaca_installation()
        self.assertEqual(status.stage, "V79.01")
        self.assertEqual(status.package_name, "alpaca-py")
        self.assertFalse(status.network_test_performed)

    def test_v79_02_default_safety_gate(self):
        config = load_safety_config({})
        self.assertFalse(config.network_allowed)
        self.assertFalse(config.broker_connected)
        self.assertFalse(config.order_submission_allowed)
        self.assertEqual(config.actual_orders_submitted, 0)

    def test_v79_02_detects_keys_without_exposing_or_using(self):
        config = load_safety_config({
            "APCA_API_KEY_ID": "do-not-print-this",
            "APCA_API_SECRET_KEY": "do-not-print-this-either",
        })
        self.assertTrue(config.credential_presence_detected)
        self.assertFalse(config.credential_values_exposed)
        self.assertFalse(config.real_credentials_used)

    def test_v79_03_request_normalizes_symbols(self):
        request = BarRequest(
            symbols=("aapl", "msft"),
            timeframe="1Min",
            start="2026-01-01T00:00:00Z",
            end="2026-01-02T00:00:00Z",
        )
        self.assertEqual(request.symbols, ("AAPL", "MSFT"))

    def test_v79_03_rejects_invalid_time_range(self):
        with self.assertRaises(ValueError):
            BarRequest(
                symbols=("AAPL",),
                timeframe="1Day",
                start="2026-01-02T00:00:00Z",
                end="2026-01-01T00:00:00Z",
            )

    def test_v79_03_rejects_inconsistent_bar(self):
        with self.assertRaises(ValueError):
            MarketBar(
                symbol="AAPL",
                timestamp="2026-01-01T00:00:00Z",
                open=100,
                high=99,
                low=98,
                close=100,
                volume=10,
            )

    def test_v79_04_offline_adapter_filters_and_sorts(self):
        config = load_safety_config({})
        bars = [
            MarketBar("AAPL", "2026-01-01T00:02:00Z", 100, 102, 99, 101, 10),
            MarketBar("AAPL", "2026-01-01T00:01:00Z", 99, 101, 98, 100, 20),
            MarketBar("MSFT", "2026-01-01T00:01:00Z", 200, 202, 199, 201, 30),
        ]
        adapter = OfflineAlpacaMarketDataAdapter(bars, config)
        request = BarRequest(
            symbols=("AAPL",),
            timeframe="1Min",
            start="2026-01-01T00:00:00Z",
            end="2026-01-01T01:00:00Z",
        )
        result = adapter.get_stock_bars(request)
        self.assertEqual([bar.close for bar in result["AAPL"]], [100, 101])
        self.assertEqual(adapter.network_call_count, 0)

    def test_v79_04_order_submission_is_blocked(self):
        adapter = OfflineAlpacaMarketDataAdapter([], load_safety_config({}))
        with self.assertRaises(RuntimeError):
            adapter.submit_order({"symbol": "AAPL"})

    def test_v79_05_certificate_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = load_safety_config({})
            bar = MarketBar("AAPL", "2026-01-01T00:00:00Z", 100, 101, 99, 100.5, 100)
            adapter = OfflineAlpacaMarketDataAdapter([bar], config)
            request = BarRequest(
                symbols=("AAPL",),
                timeframe="1Min",
                start="2025-12-31T23:00:00Z",
                end="2026-01-01T01:00:00Z",
            )
            cert = build_foundation_certificate(
                root,
                root / "release" / "v79_05" / "output",
                inspect_alpaca_installation(),
                config,
                adapter.get_stock_bars(request),
                adapter.diagnostics(),
            )
            self.assertEqual(cert["status"], "PASS")
            self.assertEqual(cert["passed_stage_count"], 5)
            self.assertEqual(cert["actual_orders_submitted"], 0)

    def test_no_secret_value_written_to_certificate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            secret = "SECRET-VALUE-MUST-NOT-APPEAR"
            config = load_safety_config({"APCA_API_KEY_ID": secret})
            bar = MarketBar("AAPL", "2026-01-01T00:00:00Z", 100, 101, 99, 100.5, 100)
            adapter = OfflineAlpacaMarketDataAdapter([bar], config)
            request = BarRequest(
                symbols=("AAPL",),
                timeframe="1Min",
                start="2025-12-31T23:00:00Z",
                end="2026-01-01T01:00:00Z",
            )
            build_foundation_certificate(
                root,
                root / "release" / "v79_05" / "output",
                inspect_alpaca_installation(),
                config,
                adapter.get_stock_bars(request),
                adapter.diagnostics(),
            )
            content = (root / "release" / "v79_05" / "output" / "alpaca_market_data_foundation_certificate_v79_05.json").read_text()
            self.assertNotIn(secret, content)

if __name__ == "__main__":
    unittest.main()
