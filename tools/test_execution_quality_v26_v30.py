import json, tempfile, unittest
from pathlib import Path
from execution_quality_v26_v30 import ExecutionQualityTimingPack

class Tests(unittest.TestCase):
    def setup_root(self, root: Path):
        brain = root / "runtime/ai_brain_v4/latest_ai_brain_report.json"
        brain.parent.mkdir(parents=True, exist_ok=True)
        brain.write_text(json.dumps({
            "multi_timeframe_ai": {
                "alignment_score": 0.82,
                "dispersion": 0.15
            },
            "explainable_final_decision": {
                "brain_score": 0.78
            },
            "multi_factor_ranking": {
                "top_candidate": {
                    "symbol": "AAPL",
                    "reference_price": 300
                }
            }
        }), encoding="utf-8")

        market = root / "runtime/market_context_v16_v20/latest_market_context_report.json"
        market.parent.mkdir(parents=True, exist_ok=True)
        market.write_text(json.dumps({
            "market_context_summary": {
                "market_entry_context": "FAVORABLE_OR_NEUTRAL"
            },
            "v16_market_regime_predictor": {
                "liquidity_score": 0.8
            }
        }), encoding="utf-8")

        guard = root / "runtime/paper_autonomous_daily_session/latest_shadow_guard_decision.json"
        guard.parent.mkdir(parents=True, exist_ok=True)
        guard.write_text(json.dumps({
            "market_snapshot": {
                "minutes_to_close": 120
            },
            "candidate": {
                "symbol": "AAPL",
                "reward_risk": 2.0
            },
            "risk_snapshot": {
                "daily_pnl": 5,
                "symbol_exposure": 400
            }
        }), encoding="utf-8")

    def test_run_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.setup_root(root)
            r = ExecutionQualityTimingPack(root).run()
            self.assertEqual(r["status"], "PASS")
            self.assertFalse(r["broker_write_performed"])

    def test_timing_not_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.setup_root(root)
            r = ExecutionQualityTimingPack(root).v26_entry_timing_quality()
            self.assertFalse(r["enforced"])
            self.assertEqual(r["order_effect"], "NONE")

    def test_notional_shadow_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.setup_root(root)
            r = ExecutionQualityTimingPack(root).v28_adaptive_notional_recommendation()
            self.assertTrue(r["shadow_only"])
            self.assertFalse(r["enforced"])
            self.assertLessEqual(r["suggested_notional"], 100)

    def test_exit_has_no_order(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.setup_root(root)
            r = ExecutionQualityTimingPack(root).v29_exit_timing_review()
            self.assertEqual(r["exit_orders_submitted"], 0)
            self.assertEqual(r["position_changes_performed"], 0)

    def test_missing_data_still_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            r = ExecutionQualityTimingPack(root).run()
            self.assertEqual(r["status"], "PASS")

    def test_outputs_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.setup_root(root)
            ExecutionQualityTimingPack(root).run()
            rt = root / "runtime/execution_quality_v26_v30"
            self.assertTrue((rt / "latest_execution_quality_report.json").exists())
            self.assertTrue((rt / "daily_execution_quality_summary.json").exists())

    def test_live_write_off(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.setup_root(root)
            r = ExecutionQualityTimingPack(root).run()
            self.assertFalse(r["etrade_live_write_enabled"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
