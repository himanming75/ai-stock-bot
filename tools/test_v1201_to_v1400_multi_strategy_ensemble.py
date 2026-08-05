from __future__ import annotations
import inspect, tempfile, unittest
from pathlib import Path
from multi_strategy_ensemble.io import write_json
from multi_strategy_ensemble.service import MultiStrategyEnsembleService

def record(symbol="SPY"):
    return {
        "symbol": symbol, "timestamp": "2026-08-05T20:00:00Z", "rank": 1,
        "close": 500, "roc_5": 0.02, "roc_10": 0.03, "return_1": 0.003,
        "return_5": 0.02, "macd_histogram": 1.1, "trend_5_20": 0.012,
        "trend_10_20": 0.008, "adx_14": 30, "plus_di_14": 28,
        "minus_di_14": 14, "price_vs_vwap": 0.006, "rsi_14": 62,
        "bollinger_percent_b": 0.8, "stochastic_14": 70,
        "volume_ratio_20": 1.4, "range_percent": 0.008,
        "atr_percent": 0.012, "bollinger_width": 0.04,
    }

class Tests(unittest.TestCase):
    def evaluate(self, root):
        f = root / "features.json"; r = root / "regime.json"
        write_json(f, {"records": [record()]})
        write_json(r, {"regime": "BULL_TREND"})
        return MultiStrategyEnsembleService().evaluate(f, r, root / "out")

    def test_six_strategies(self):
        with tempfile.TemporaryDirectory() as d:
            result = self.evaluate(Path(d))
            self.assertEqual(len(result["ranked_ensemble_results"][0]["strategy_results"]), 6)

    def test_ensemble_output(self):
        with tempfile.TemporaryDirectory() as d:
            result = self.evaluate(Path(d))
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["ensemble_record_count"], 1)

    def test_empty_features_block(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            f = root / "f.json"; r = root / "r.json"
            write_json(f, {"records": []}); write_json(r, {"regime": "UNKNOWN"})
            result = MultiStrategyEnsembleService().evaluate(f, r, root / "out")
            self.assertEqual(result["status"], "BLOCKED")

    def test_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.evaluate(root)
            self.assertTrue((root / "out/ensemble_dataset_latest.csv").exists())
            self.assertTrue((root / "out/strategy_signal_store.jsonl").exists())

    def test_zero_order_contract(self):
        source = inspect.getsource(MultiStrategyEnsembleService)
        self.assertIn('"actual_broker_write_performed": False', source)
        self.assertIn('"actual_paper_orders_submitted": 0', source)
        self.assertIn('"actual_live_orders_submitted": 0', source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
