import json
import tempfile
import unittest
from pathlib import Path

from shadow_validation_v11_v15 import ShadowValidationIntelligence


class Tests(unittest.TestCase):
    def setup_root(self, root: Path):
        v5 = root / "runtime/ai_strategy_ensemble_v5/latest_ensemble_report.json"
        v5.parent.mkdir(parents=True, exist_ok=True)
        v5.write_text(json.dumps({
            "candidate": {"side": "BUY"},
            "ensemble": {
                "weighted_score": 0.60,
                "avoid_votes": 3,
                "agreement_ratio": 0.50
            }
        }), encoding="utf-8")

        v6 = root / "runtime/shadow_intelligence_v6_v10/latest_shadow_intelligence_report.json"
        v6.parent.mkdir(parents=True, exist_ok=True)
        v6.write_text(json.dumps({
            "market_regime_engine": {"label": "UNCERTAIN"},
            "multi_timeframe_intelligence": {
                "alignment": "BULLISH_ALIGNMENT"
            },
            "position_quality_analyzer": {"grade": "D"},
            "explainable_ai_report": {
                "caution_reasons": ["REGIME_UNCERTAIN"]
            }
        }), encoding="utf-8")

        guard = root / "runtime/paper_autonomous_daily_session/latest_shadow_guard_decision.json"
        guard.parent.mkdir(parents=True, exist_ok=True)
        guard.write_text(json.dumps({
            "issues": [
                {"code": "DUPLICATE_SYMBOL_BUY"},
                {"code": "SYMBOL_EXPOSURE_LIMIT"}
            ]
        }), encoding="utf-8")

    def test_run_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = ShadowValidationIntelligence(root).run()
            self.assertEqual(result["status"], "PASS")
            self.assertFalse(result["broker_write_performed"])

    def test_false_signal_not_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = ShadowValidationIntelligence(
                root
            ).false_signal_detector()
            self.assertFalse(result["enforced"])
            self.assertEqual(result["order_effect"], "NONE")

    def test_replay_submits_no_orders(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = ShadowValidationIntelligence(root).trade_replay()
            self.assertEqual(result["orders_submitted_during_replay"], 0)

    def test_readiness_advisory_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = ShadowValidationIntelligence(
                root
            ).live_readiness_dashboard()
            self.assertFalse(result["live_submission_enabled"])
            self.assertEqual(
                result["certification_effect"], "ADVISORY_ONLY"
            )

    def test_missing_data_still_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            result = ShadowValidationIntelligence(root).run()
            self.assertEqual(result["status"], "PASS")

    def test_outputs_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            ShadowValidationIntelligence(root).run()
            runtime = root / "runtime/shadow_validation_v11_v15"
            self.assertTrue(
                (runtime / "latest_validation_report.json").exists()
            )
            self.assertTrue(
                (runtime / "daily_validation_summary.json").exists()
            )

    def test_live_write_off(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = ShadowValidationIntelligence(root).run()
            self.assertFalse(result["etrade_live_write_enabled"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
