import json
import tempfile
import unittest
from pathlib import Path

from ai_strategy_ensemble_v5 import StrategyEnsembleShadowReview


class Tests(unittest.TestCase):
    def setup_root(self, root: Path):
        v2 = root / "runtime/ai_intelligence_safety_v2/latest_intelligence_report.json"
        v2.parent.mkdir(parents=True, exist_ok=True)
        v2.write_text(json.dumps({
            "candidate": {
                "symbol": "AAPL",
                "side": "BUY",
                "confidence": 0.91,
                "consensus_score": 0.95,
                "reward_risk": 2.0
            },
            "multi_score": {
                "trend_score": 0.90,
                "momentum_score": 0.92,
                "breakout_score": 0.80
            },
            "market_regime": {
                "market_regime_fit": 0.70,
                "volatility_risk": 0.40
            },
            "safety_heatmap": {
                "level": "LOW"
            }
        }), encoding="utf-8")

        guard = root / "runtime/paper_autonomous_daily_session/latest_shadow_guard_decision.json"
        guard.parent.mkdir(parents=True, exist_ok=True)
        guard.write_text(json.dumps({
            "candidate": {
                "symbol": "AAPL",
                "side": "BUY",
                "confidence": 0.91,
                "consensus_score": 0.95,
                "reward_risk": 2.0
            },
            "issues": []
        }), encoding="utf-8")

    def test_run_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = StrategyEnsembleShadowReview(root).run()
            self.assertEqual(result["status"], "PASS")
            self.assertFalse(result["broker_write_performed"])

    def test_ensemble_not_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = StrategyEnsembleShadowReview(root).ensemble()
            self.assertFalse(result["enforced"])
            self.assertEqual(result["order_effect"], "NONE")

    def test_strategy_score_range(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            scores = StrategyEnsembleShadowReview(root).strategy_scores()
            for value in scores.values():
                self.assertGreaterEqual(value, 0)
                self.assertLessEqual(value, 1)

    def test_no_automatic_weight_changes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = StrategyEnsembleShadowReview(
                root
            ).strategy_performance_memory()
            self.assertFalse(result["automatic_weight_changes"])

    def test_missing_data_still_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            result = StrategyEnsembleShadowReview(root).run()
            self.assertEqual(result["status"], "PASS")

    def test_outputs_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            StrategyEnsembleShadowReview(root).run()
            runtime = root / "runtime/ai_strategy_ensemble_v5"
            self.assertTrue(
                (runtime / "latest_ensemble_report.json").exists()
            )
            self.assertTrue(
                (runtime / "daily_ensemble_summary.json").exists()
            )

    def test_live_write_off(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = StrategyEnsembleShadowReview(root).run()
            self.assertFalse(result["etrade_live_write_enabled"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
