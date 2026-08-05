from __future__ import annotations
import inspect
import tempfile
import unittest
from pathlib import Path

from ai_market_intelligence.indicators import feature_record
from ai_market_intelligence.io import write_json
from ai_market_intelligence.service import AIMarketIntelligenceService


def bars(count=60, start=100.0):
    result = []
    for i in range(count):
        close = start + i * 0.25 + ((i % 5) - 2) * 0.05
        result.append({
            "t": f"2026-08-05T{13 + i // 60:02d}:{i % 60:02d}:00Z",
            "o": close - 0.1,
            "h": close + 0.3,
            "l": close - 0.3,
            "c": close,
            "v": 1000 + i * 10,
        })
    return result


class Tests(unittest.TestCase):
    def test_feature_record_contains_indicators(self):
        record = feature_record("SPY", bars())
        self.assertIsNotNone(record["rsi_14"])
        self.assertIsNotNone(record["macd"])
        self.assertIsNotNone(record["atr_14"])
        self.assertIsNotNone(record["vwap"])

    def test_service_builds_ranked_features(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "snapshot.json"
            write_json(snapshot, {"bars_by_symbol": {"SPY": bars(), "QQQ": bars(start=200)}})
            result = AIMarketIntelligenceService().evaluate(
                snapshot_path=snapshot,
                output_dir=root / "out",
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["feature_record_count"], 2)
            self.assertEqual(result["ranked_symbols"][0]["rank"], 1)

    def test_insufficient_bars_blocks_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "snapshot.json"
            write_json(snapshot, {"bars_by_symbol": {"SPY": bars(20)}})
            result = AIMarketIntelligenceService().evaluate(
                snapshot_path=snapshot,
                output_dir=root / "out",
            )
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["quality_failure_count"], 1)

    def test_outputs_created(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            snapshot = root / "snapshot.json"
            write_json(snapshot, {"bars_by_symbol": {"SPY": bars()}})
            AIMarketIntelligenceService().evaluate(
                snapshot_path=snapshot,
                output_dir=root / "out",
            )
            self.assertTrue((root / "out/feature_dataset_latest.csv").exists())
            self.assertTrue((root / "out/feature_store.jsonl").exists())

    def test_zero_order_contract(self):
        source = inspect.getsource(AIMarketIntelligenceService)
        self.assertIn('"actual_broker_write_performed": False', source)
        self.assertIn('"actual_paper_orders_submitted": 0', source)
        self.assertIn('"actual_live_orders_submitted": 0', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
