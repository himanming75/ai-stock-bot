import json, tempfile, unittest
from pathlib import Path
from ai_brain_v4 import AIBrainV4

class Tests(unittest.TestCase):
    def setup_root(self, root: Path):
        obs = root / "runtime/paper_observability_intelligence/latest_observability_report.json"
        obs.parent.mkdir(parents=True, exist_ok=True)
        obs.write_text(json.dumps({
            "top_candidates": [
                {
                    "rank": 1,
                    "symbol": "AAPL",
                    "side": "BUY",
                    "confidence": 0.91,
                    "consensus_score": 0.95,
                    "reward_risk": 2.0
                },
                {
                    "rank": 2,
                    "symbol": "MSFT",
                    "side": "BUY",
                    "confidence": 0.85,
                    "consensus_score": 0.88,
                    "reward_risk": 1.8
                }
            ]
        }), encoding="utf-8")

        v6 = root / "runtime/shadow_intelligence_v6_v10/latest_shadow_intelligence_report.json"
        v6.parent.mkdir(parents=True, exist_ok=True)
        v6.write_text(json.dumps({
            "multi_timeframe_intelligence": {
                "timeframes": {"1m": 0.8, "5m": 0.82, "15m": 0.84, "1h": 0.80}
            }
        }), encoding="utf-8")

        v5 = root / "runtime/ai_strategy_ensemble_v5/latest_ensemble_report.json"
        v5.parent.mkdir(parents=True, exist_ok=True)
        v5.write_text(json.dumps({
            "ensemble": {"weighted_score": 0.78}
        }), encoding="utf-8")

        v16 = root / "runtime/market_context_v16_v20/latest_market_context_report.json"
        v16.parent.mkdir(parents=True, exist_ok=True)
        v16.write_text(json.dumps({
            "market_context_summary": {
                "market_entry_context": "FAVORABLE_OR_NEUTRAL"
            }
        }), encoding="utf-8")

    def test_run_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.setup_root(root)
            r = AIBrainV4(root).run()
            self.assertEqual(r["status"], "PASS")
            self.assertFalse(r["broker_write_performed"])

    def test_ranking_exists(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.setup_root(root)
            r = AIBrainV4(root).multi_factor_ranking()
            self.assertEqual(r["status"], "PASS")
            self.assertEqual(len(r["ranked_candidates"]), 2)

    def test_no_candidate_replacement(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.setup_root(root)
            r = AIBrainV4(root).multi_factor_ranking()
            self.assertFalse(r["automatic_candidate_replacement"])
            self.assertEqual(r["order_effect"], "NONE")

    def test_decision_not_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.setup_root(root)
            r = AIBrainV4(root).explainable_final_decision()
            self.assertFalse(r["enforced"])
            self.assertEqual(r["order_effect"], "NONE")

    def test_missing_data_still_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            r = AIBrainV4(root).run()
            self.assertEqual(r["status"], "PASS")

    def test_outputs_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.setup_root(root)
            AIBrainV4(root).run()
            rt = root / "runtime/ai_brain_v4"
            self.assertTrue((rt / "latest_ai_brain_report.json").exists())
            self.assertTrue((rt / "daily_ai_brain_summary.json").exists())

    def test_live_write_off(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.setup_root(root)
            r = AIBrainV4(root).run()
            self.assertFalse(r["etrade_live_write_enabled"])

if __name__ == "__main__":
    unittest.main(verbosity=2)
