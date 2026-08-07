import json
import tempfile
import unittest
from pathlib import Path

from shadow_intelligence_v6_v10 import ShadowIntelligencePack


class Tests(unittest.TestCase):
    def setup_root(self, root: Path):
        v2 = root / "runtime/ai_intelligence_safety_v2/latest_intelligence_report.json"
        v2.parent.mkdir(parents=True, exist_ok=True)
        v2.write_text(json.dumps({
            "multi_score": {
                "trend_score": 0.9,
                "momentum_score": 0.9,
                "breakout_score": 0.8
            },
            "market_regime": {
                "market_regime_fit": 0.7,
                "volatility_risk": 0.4
            }
        }), encoding="utf-8")

        v5 = root / "runtime/ai_strategy_ensemble_v5/latest_ensemble_report.json"
        v5.parent.mkdir(parents=True, exist_ok=True)
        v5.write_text(json.dumps({
            "candidate": {
                "symbol": "AAPL",
                "side": "BUY",
                "confidence": 0.91,
                "consensus_score": 0.95,
                "reward_risk": 2.0
            },
            "ensemble": {
                "weighted_score": 0.8,
                "decision": "BUY_OBSERVATION"
            },
            "decision_comparison": {
                "comparison": "DIRECTIONAL_AGREEMENT"
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
            "risk_snapshot": {
                "symbol_exposure": 600,
                "daily_pnl": 5,
                "open_positions": 2
            },
            "policy": {
                "maximum_symbol_exposure": 500,
                "maximum_open_positions": 2
            }
        }), encoding="utf-8")

    def test_run_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = ShadowIntelligencePack(root).run()
            self.assertEqual(result["status"], "PASS")
            self.assertFalse(result["broker_write_performed"])

    def test_multi_timeframe_not_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = ShadowIntelligencePack(root).multi_timeframe()
            self.assertFalse(result["enforced"])
            self.assertEqual(result["order_effect"], "NONE")

    def test_regime_does_not_change_weights(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = ShadowIntelligencePack(root).market_regime()
            self.assertFalse(result["strategy_weights_changed"])

    def test_position_analyzer_no_changes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = ShadowIntelligencePack(root).position_quality()
            self.assertFalse(result["enforced"])
            self.assertEqual(result["position_changes_performed"], 0)

    def test_missing_data_still_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            result = ShadowIntelligencePack(root).run()
            self.assertEqual(result["status"], "PASS")

    def test_outputs_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            ShadowIntelligencePack(root).run()
            runtime = root / "runtime/shadow_intelligence_v6_v10"
            self.assertTrue(
                (runtime / "latest_shadow_intelligence_report.json").exists()
            )
            self.assertTrue(
                (runtime / "daily_shadow_intelligence_summary.json").exists()
            )

    def test_live_write_off(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = ShadowIntelligencePack(root).run()
            self.assertFalse(result["etrade_live_write_enabled"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
