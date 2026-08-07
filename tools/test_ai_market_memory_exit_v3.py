import json
import tempfile
import unittest
from pathlib import Path

from ai_market_memory_v3 import MarketMemoryExitIntelligence


class Tests(unittest.TestCase):
    def setup_root(self, root: Path):
        v2 = root / "runtime/ai_intelligence_safety_v2/latest_intelligence_report.json"
        v2.parent.mkdir(parents=True, exist_ok=True)
        v2.write_text(json.dumps({
            "multi_score": {
                "trend_score": 0.9,
                "momentum_score": 0.9,
                "breakout_score": 0.8,
                "total_score": 0.85
            },
            "market_regime": {
                "market_regime_fit": 0.7
            },
            "safety_heatmap": {
                "level": "HIGH"
            }
        }), encoding="utf-8")

        guard = root / "runtime/paper_autonomous_daily_session/latest_shadow_guard_decision.json"
        guard.parent.mkdir(parents=True, exist_ok=True)
        guard.write_text(json.dumps({
            "candidate": {
                "symbol": "AAPL",
                "reward_risk": 2.0
            },
            "risk_snapshot": {
                "symbol_exposure": 500,
                "daily_pnl": 5
            }
        }), encoding="utf-8")

    def test_run_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = MarketMemoryExitIntelligence(root).run()
            self.assertEqual(result["status"], "PASS")
            self.assertFalse(result["broker_write_performed"])

    def test_ensemble_not_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            vote = MarketMemoryExitIntelligence(root).ensemble_vote()
            self.assertFalse(vote["enforced"])
            self.assertEqual(vote["order_effect"], "NONE")

    def test_exit_is_advisory_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            exit_data = MarketMemoryExitIntelligence(root).exit_intelligence()
            self.assertEqual(exit_data["exit_orders_submitted"], 0)
            self.assertEqual(exit_data["position_changes_performed"], 0)

    def test_missing_data_still_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            result = MarketMemoryExitIntelligence(root).run()
            self.assertEqual(result["status"], "PASS")

    def test_output_files_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            MarketMemoryExitIntelligence(root).run()
            runtime = root / "runtime/ai_market_memory_v3"
            self.assertTrue(
                (runtime / "latest_market_memory_report.json").exists()
            )
            self.assertTrue(
                (runtime / "daily_memory_review.json").exists()
            )

    def test_live_write_off(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = MarketMemoryExitIntelligence(root).run()
            self.assertFalse(result["etrade_live_write_enabled"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
