import json
import tempfile
import unittest
from pathlib import Path

from trade_classification_v56_v60 import TradeClassificationAttribution


class Tests(unittest.TestCase):
    def setup_root(self, root: Path):
        ledger = (
            root
            / "runtime/closed_trade_outcome_v41_v45/"
              "closed_trade_outcomes.jsonl"
        )
        ledger.parent.mkdir(parents=True, exist_ok=True)
        rows = [
            {
                "trade_id": "T1",
                "symbol": "AAPL",
                "side": "LONG",
                "entry_time": "2026-08-01T14:00:00+00:00",
                "exit_time": "2026-08-01T15:00:00+00:00",
                "realized_pl": 10.0,
                "realized_return": 0.02,
                "strategy": "MOMENTUM"
            },
            {
                "trade_id": "T2",
                "symbol": "SPY",
                "side": "LONG",
                "entry_time": "2026-08-01T14:00:00+00:00",
                "exit_time": "2026-08-02T14:00:00+00:00",
                "realized_pl": -5.0,
                "realized_return": -0.01,
                "strategy": "TREND"
            }
        ]
        with ledger.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")

    def test_run_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            r = TradeClassificationAttribution(root).run()
            self.assertEqual(r["status"], "PASS")
            self.assertFalse(r["broker_write_performed"])

    def test_classification(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            r = TradeClassificationAttribution(
                root
            ).v56_closed_trade_classifier()
            self.assertEqual(r["trade_count"], 2)
            self.assertEqual(
                r["classified_trades"][0]["outcome_class"],
                "WIN",
            )

    def test_holding_period(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            r = TradeClassificationAttribution(
                root
            ).v57_holding_period_analyzer()
            self.assertEqual(r["trade_count"], 2)

    def test_strategy_attribution_no_auto_select(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            r = TradeClassificationAttribution(
                root
            ).v58_strategy_signal_attribution()
            self.assertFalse(r["automatic_strategy_selection"])

    def test_tagging_no_filtering(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            r = TradeClassificationAttribution(
                root
            ).v59_trade_tagging_context()
            self.assertFalse(r["automatic_filtering"])

    def test_missing_data_still_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            r = TradeClassificationAttribution(root).run()
            self.assertEqual(r["status"], "PASS")

    def test_outputs_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            TradeClassificationAttribution(root).run()
            rt = root / "runtime/trade_classification_v56_v60"
            self.assertTrue(
                (rt / "latest_trade_classification_report.json").exists()
            )
            self.assertTrue(
                (rt / "performance_attribution_dataset.json").exists()
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
