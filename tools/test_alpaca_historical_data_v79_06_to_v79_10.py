import json
import tempfile
import unittest
from pathlib import Path

from alpaca_market_data import (
    AlpacaRequestFactory,
    FixtureHistoricalTransport,
    HistoricalBarRecord,
    HistoricalBarsQuery,
    HistoricalClientConfig,
    HistoricalDataCache,
    HistoricalDataNormalizer,
    SafeHistoricalDataService,
    build_historical_certificate,
    inspect_historical_installation,
)

class HistoricalDataTests(unittest.TestCase):
    def test_v79_06_installation_contract(self):
        status = inspect_historical_installation()
        self.assertTrue(status.alpaca_py_installed)
        self.assertTrue(status.stock_historical_client_importable)
        self.assertTrue(status.stock_bars_request_importable)
        self.assertFalse(status.network_test_performed)

    def test_v79_06_safety_config(self):
        config = HistoricalClientConfig()
        config.validate()
        self.assertFalse(config.network_allowed)
        self.assertFalse(config.credentials_used)
        self.assertFalse(config.trading_client_created)

    def test_v79_07_query_normalization(self):
        query = HistoricalBarsQuery(
            ("aapl", "msft"), "1Min",
            "2026-01-01T00:00:00", "2026-01-02T00:00:00Z"
        )
        self.assertEqual(query.symbols, ("AAPL", "MSFT"))
        self.assertTrue(query.start.endswith("Z"))

    def test_v79_07_invalid_query_rejected(self):
        with self.assertRaises(ValueError):
            HistoricalBarsQuery(
                ("AAPL",), "2Min",
                "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"
            )

    def test_v79_07_official_request_object_builds_without_http(self):
        query = HistoricalBarsQuery(
            ("AAPL",), "5Min",
            "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"
        )
        request = AlpacaRequestFactory.build_stock_bars_request(query)
        self.assertEqual(type(request).__name__, "StockBarsRequest")


    def test_v79_07_sort_import_uses_common_enums(self):
        module_text = (
            Path(__file__).resolve().parents[1]
            / "alpaca_market_data/historical_v79_06_10.py"
        ).read_text(encoding="utf-8")
        self.assertIn("from alpaca.common.enums import Sort", module_text)
        self.assertNotIn("from alpaca.data.enums import Adjustment, DataFeed, Sort", module_text)

    def test_v79_08_normalizer_orders_records(self):
        payload = {
            "AAPL": [
                {"timestamp": "2026-01-01T00:02:00Z", "open": 101, "high": 102, "low": 100, "close": 101.5, "volume": 20},
                {"timestamp": "2026-01-01T00:01:00Z", "open": 100, "high": 101, "low": 99, "close": 100.5, "volume": 10},
            ]
        }
        rows = HistoricalDataNormalizer.normalize(payload)
        self.assertEqual([row.timestamp for row in rows], [
            "2026-01-01T00:01:00Z", "2026-01-01T00:02:00Z"
        ])

    def test_v79_08_bad_ohlc_rejected(self):
        with self.assertRaises(ValueError):
            HistoricalBarRecord("AAPL", "2026-01-01T00:00:00Z", 100, 99, 98, 100, 1)

    def test_v79_09_cache_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            query = HistoricalBarsQuery(
                ("AAPL",), "1Min",
                "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"
            )
            rows = [HistoricalBarRecord("AAPL", "2026-01-01T00:01:00Z", 100, 101, 99, 100.5, 10)]
            cache = HistoricalDataCache(Path(tmp))
            cache.put(query, rows)
            self.assertEqual(cache.get(query), rows)

    def test_v79_09_cache_tamper_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            query = HistoricalBarsQuery(
                ("AAPL",), "1Min",
                "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"
            )
            rows = [HistoricalBarRecord("AAPL", "2026-01-01T00:01:00Z", 100, 101, 99, 100.5, 10)]
            cache = HistoricalDataCache(Path(tmp))
            cache.put(query, rows)
            data_path = Path(tmp) / f"{query.cache_key}.json"
            data_path.write_text("tampered", encoding="utf-8")
            with self.assertRaises(ValueError):
                cache.get(query)

    def test_service_uses_cache_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            query = HistoricalBarsQuery(
                ("AAPL",), "1Min",
                "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"
            )
            transport = FixtureHistoricalTransport({"AAPL": [{
                "timestamp": "2026-01-01T00:01:00Z", "open": 100,
                "high": 101, "low": 99, "close": 100.5, "volume": 10
            }]})
            service = SafeHistoricalDataService(
                HistoricalClientConfig(), transport, HistoricalDataCache(Path(tmp))
            )
            first = service.get_bars(query)
            second = service.get_bars(query)
            self.assertEqual(first, second)
            self.assertEqual(transport.fixture_fetch_count, 1)
            self.assertEqual(transport.network_call_count, 0)
            self.assertEqual(service.cache_hit_count, 1)

    def test_v79_10_certificate_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            foundation = root / "release/v79_05/output/alpaca_market_data_foundation_certificate_v79_05.json"
            foundation.parent.mkdir(parents=True)
            foundation.write_text('{"status":"PASS"}', encoding="utf-8")
            query = HistoricalBarsQuery(
                ("AAPL",), "1Min",
                "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"
            )
            transport = FixtureHistoricalTransport({"AAPL": [{
                "timestamp": "2026-01-01T00:01:00Z", "open": 100,
                "high": 101, "low": 99, "close": 100.5, "volume": 10
            }]})
            cache = HistoricalDataCache(root / "cache")
            service = SafeHistoricalDataService(HistoricalClientConfig(), transport, cache)
            rows = service.get_bars(query)
            manifest = json.loads((root / "cache" / f"{query.cache_key}.manifest.json").read_text())
            cert = build_historical_certificate(
                root, root / "release/v79_10/output",
                inspect_historical_installation(), HistoricalClientConfig(),
                query, rows, service.diagnostics(), manifest
            )
            self.assertEqual(cert["status"], "PASS")
            self.assertEqual(cert["passed_stage_count"], 5)
            self.assertEqual(cert["network_calls_made"], 0)

    def test_no_trading_or_order_client_imports(self):
        module_text = (Path(__file__).resolve().parents[1] / "alpaca_market_data/historical_v79_06_10.py").read_text()
        self.assertNotIn("TradingClient", module_text)
        self.assertNotIn("submit_order(", module_text)

if __name__ == "__main__":
    unittest.main()
