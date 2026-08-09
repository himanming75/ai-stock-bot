
from pathlib import Path
import importlib.util
import tempfile
import json
import unittest


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load(Path("dashboard/canonical_lifecycle_source_v3_8.py"), "v38_test")

    def test_canonical_trade_normalization(self):
        row = {
            "trade_id": "paper-roundtrip-aapl-1",
            "symbol": "AAPL",
            "entry_price": 200,
            "exit_price": 202,
            "quantity": 2,
            "realized_pl": 4,
            "exit_time": "2026-08-07T00:00:00+00:00",
            "exit_order_id": "order-1",
        }
        trade = self.m.normalize_canonical_trade(row, "fixture")
        self.assertEqual(trade["pnl"], 4.0)
        self.assertTrue(trade["canonical_actual_round_trip"])

    def test_canonical_path_exact(self):
        self.assertEqual(
            str(self.m.CANONICAL_CLOSED).replace("\\", "/"),
            "runtime/paper_full_auto_lifecycle/closed_round_trips.jsonl",
        )

    def test_discovery_reads_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root/self.m.CANONICAL_CLOSED
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps({
                    "trade_id": "t1",
                    "symbol": "AAPL",
                    "entry_price": 100,
                    "exit_price": 101,
                    "quantity": 1,
                    "realized_pl": 1,
                    "exit_time": "2026-08-07T00:00:00+00:00",
                }) + "\n",
                encoding="utf-8",
            )
            result = self.m.build_lifecycle_discovery(root)
            self.assertEqual(result["counts"]["canonical_numeric_pnl_count"], 1)

    def test_missing_canonical_is_safe(self):
        with tempfile.TemporaryDirectory() as td:
            result = self.m.build_lifecycle_discovery(Path(td))
            self.assertEqual(result["status"], "PASS_CANONICAL_EMPTY")

    def test_read_only(self):
        text = Path("dashboard/canonical_lifecycle_source_v3_8.py").read_text(encoding="utf-8")
        for bad in ("TradingClient(", "submit_order(", "MarketOrderRequest("):
            self.assertNotIn(bad, text)


if __name__ == "__main__":
    unittest.main()
