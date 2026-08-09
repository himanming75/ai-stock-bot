
from pathlib import Path
import importlib.util
import unittest


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.n = load(
            Path("dashboard/trade_ledger_normalizer_v3_6.py"),
            "v36_normalizer_test",
        )

    def test_nested_realized_pl(self):
        record = {
            "event_type": "CLOSED_TRADE",
            "payload": {
                "symbol": "AAPL",
                "performance": {
                    "realized_pl": "0.04354467"
                },
            },
        }
        trade = self.n.normalize_closed_trade(record, "fixture")
        self.assertAlmostEqual(trade["pnl"], 0.04354467)
        self.assertEqual(
            trade["normalization"]["pnl_path"],
            "payload.performance.realized_pl",
        )

    def test_realized_key_beats_generic_pnl(self):
        record = {
            "event": "CLOSED_TRADE",
            "pnl": 999,
            "details": {"realized_pnl": 1.25},
        }
        trade = self.n.normalize_closed_trade(record, "fixture")
        self.assertEqual(trade["pnl"], 1.25)

    def test_non_numeric_not_invented(self):
        record = {
            "event": "CLOSED_TRADE",
            "details": {"realized_pnl": None},
        }
        trade = self.n.normalize_closed_trade(record, "fixture")
        self.assertIsNone(trade["pnl"])

    def test_nested_metadata(self):
        record = {
            "wrapper": {
                "event": "CLOSED_TRADE",
                "data": {
                    "symbol": "MSFT",
                    "quantity": "2",
                    "reason": "TIME_EXIT",
                    "pnl": "3.5",
                },
            },
        }
        trade = self.n.normalize_closed_trade(record, "fixture")
        self.assertEqual(trade["symbol"], "MSFT")
        self.assertEqual(trade["qty"], 2.0)
        self.assertEqual(trade["reason"], "TIME_EXIT")

    def test_read_only_module(self):
        text = Path(
            "dashboard/trade_ledger_normalizer_v3_6.py"
        ).read_text(encoding="utf-8")
        for bad in (
            "TradingClient(",
            "submit_order(",
            "place_order(",
            "MarketOrderRequest(",
        ):
            self.assertNotIn(bad, text)


if __name__ == "__main__":
    unittest.main()
