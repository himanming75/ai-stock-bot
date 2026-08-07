import json, tempfile, unittest
from pathlib import Path
from performance_intelligence_v21_v25 import PerformanceIntelligencePack

class Tests(unittest.TestCase):
    def setup_root(self, root: Path):
        p = root / "runtime/closed_trade_calibration_v4/latest_calibration_report.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "linked_outcomes": [
                {
                    "trade_id": "T1",
                    "symbol": "AAPL",
                    "entry_time": "2026-08-03T14:00:00+00:00",
                    "exit_time": "2026-08-03T15:00:00+00:00",
                    "realized_pl": 10.0,
                    "market_regime": "BULL_TREND",
                    "candidate": {
                        "guard_action": "SHADOW_ALLOW",
                        "confidence": 0.91
                    }
                },
                {
                    "trade_id": "T2",
                    "symbol": "MSFT",
                    "entry_time": "2026-08-04T15:00:00+00:00",
                    "exit_time": "2026-08-04T16:00:00+00:00",
                    "realized_pl": -5.0,
                    "market_regime": "SIDEWAYS",
                    "candidate": {
                        "guard_action": "SHADOW_BLOCK",
                        "confidence": 0.84
                    }
                }
            ]
        }), encoding="utf-8")

    def test_run_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.setup_root(root)
            r = PerformanceIntelligencePack(root).run()
            self.assertEqual(r["status"], "PASS")
            self.assertFalse(r["broker_write_performed"])

    def test_symbol_memory(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.setup_root(root)
            r = PerformanceIntelligencePack(root).symbol_performance_memory()
            self.assertEqual(r["status"], "PASS")
            self.assertEqual(r["best_symbol"], "AAPL")

    def test_regime_matrix(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.setup_root(root)
            r = PerformanceIntelligencePack(root).regime_conditioned_performance()
            self.assertEqual(r["outcome_regime_linked_count"], 2)

    def test_counterfactual_no_enforcement(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.setup_root(root)
            r = PerformanceIntelligencePack(root).counterfactual_shadow_review()
            self.assertFalse(r["guard_enforcement_changed"])
            self.assertEqual(r["order_effect"], "NONE")

    def test_missing_data_collects(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            r = PerformanceIntelligencePack(root).run()
            self.assertEqual(r["status"], "PASS")
            self.assertEqual(
                r["v21_symbol_performance_memory"]["status"], "COLLECTING_DATA"
            )

    def test_outputs_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.setup_root(root)
            PerformanceIntelligencePack(root).run()
            rt = root / "runtime/performance_intelligence_v21_v25"
            self.assertTrue((rt / "latest_performance_intelligence_report.json").exists())
            self.assertTrue((rt / "daily_performance_intelligence_summary.json").exists())

    def test_live_write_off(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.setup_root(root)
            r = PerformanceIntelligencePack(root).run()
            self.assertFalse(r["etrade_live_write_enabled"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
