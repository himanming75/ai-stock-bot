import json
import tempfile
import unittest
from pathlib import Path

from closed_trade_analytics_v46_v50 import ClosedTradeAnalyticsReadiness


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
                "realized_pl": 10.0,
                "market_regime": "BULL"
            },
            {
                "trade_id": "T2",
                "symbol": "AAPL",
                "realized_pl": -5.0,
                "market_regime": "SIDEWAYS"
            },
            {
                "trade_id": "T3",
                "symbol": "SPY",
                "realized_pl": 8.0,
                "market_regime": "BULL"
            }
        ]
        with ledger.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")

    def test_run_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            r = ClosedTradeAnalyticsReadiness(root).run()
            self.assertEqual(r["status"], "PASS")
            self.assertFalse(r["broker_write_performed"])

    def test_performance_metrics(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            r = ClosedTradeAnalyticsReadiness(
                root
            ).v47_core_performance_metrics()
            self.assertEqual(r["trade_count"], 3)
            self.assertAlmostEqual(r["total_realized_pl"], 13.0)

    def test_drawdown(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            r = ClosedTradeAnalyticsReadiness(
                root
            ).v48_drawdown_loss_streak()
            self.assertLessEqual(r["max_drawdown"], 0)

    def test_symbol_breakdown(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            r = ClosedTradeAnalyticsReadiness(
                root
            ).v49_symbol_regime_breakdown()
            self.assertGreaterEqual(len(r["symbol_breakdown"]), 2)

    def test_readiness_is_advisory(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            r = ClosedTradeAnalyticsReadiness(
                root
            ).v50_readiness_gate()
            self.assertFalse(r["live_submission_enabled"])
            self.assertEqual(r["deployment_effect"], "ADVISORY_ONLY")

    def test_missing_data_still_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            r = ClosedTradeAnalyticsReadiness(root).run()
            self.assertEqual(r["status"], "PASS")

    def test_outputs_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            ClosedTradeAnalyticsReadiness(root).run()
            rt = root / "runtime/closed_trade_analytics_v46_v50"
            self.assertTrue(
                (rt / "latest_closed_trade_analytics_report.json").exists()
            )
            self.assertTrue(
                (rt / "daily_closed_trade_analytics_summary.json").exists()
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
