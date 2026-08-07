import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from decision_robustness_v31_v35 import DataQualityDecisionRobustness


class Tests(unittest.TestCase):
    def setup_root(self, root: Path):
        now = datetime.now(timezone.utc).isoformat()

        brain = root / "runtime/ai_brain_v4/latest_ai_brain_report.json"
        brain.parent.mkdir(parents=True, exist_ok=True)
        brain.write_text(json.dumps({
            "generated_at_utc": now,
            "multi_factor_ranking": {
                "top_candidate": {
                    "symbol": "AAPL",
                    "confidence": 0.91,
                    "consensus_score": 0.95,
                    "reward_risk": 2.0,
                    "score": 0.75,
                    "components": {
                        "confidence": 0.91,
                        "consensus": 0.95,
                        "multi_timeframe": 0.80,
                        "market_penalty": 0.10
                    }
                }
            },
            "multi_timeframe_ai": {
                "direction": "BULLISH"
            },
            "explainable_final_decision": {
                "decision": "BUY_OR_WATCH_OBSERVATION",
                "brain_score": 0.75
            }
        }), encoding="utf-8")

        execution = root / "runtime/execution_quality_v26_v30/latest_execution_quality_report.json"
        execution.parent.mkdir(parents=True, exist_ok=True)
        execution.write_text(json.dumps({
            "generated_at_utc": now,
            "v26_entry_timing_quality": {
                "timing_state": "ACCEPTABLE_WINDOW"
            }
        }), encoding="utf-8")

        market = root / "runtime/market_context_v16_v20/latest_market_context_report.json"
        market.parent.mkdir(parents=True, exist_ok=True)
        market.write_text(json.dumps({
            "generated_at_utc": now,
            "market_context_summary": {
                "market_entry_context": "FAVORABLE_OR_NEUTRAL"
            }
        }), encoding="utf-8")

        guard = root / "runtime/paper_autonomous_daily_session/latest_shadow_guard_decision.json"
        guard.parent.mkdir(parents=True, exist_ok=True)
        guard.write_text(json.dumps({
            "observed_at_utc": now
        }), encoding="utf-8")

    def test_run_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = DataQualityDecisionRobustness(root).run()
            self.assertEqual(result["status"], "PASS")
            self.assertFalse(result["broker_write_performed"])

    def test_data_quality_present(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = DataQualityDecisionRobustness(
                root
            ).v31_data_quality_audit()
            self.assertNotIn("brain", result["missing_sources"])

    def test_conflict_not_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = DataQualityDecisionRobustness(
                root
            ).v32_signal_conflict_detector()
            self.assertFalse(result["enforced"])
            self.assertEqual(result["order_effect"], "NONE")

    def test_sensitivity_has_scenarios(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = DataQualityDecisionRobustness(
                root
            ).v33_score_sensitivity()
            self.assertEqual(result["scenario_count"], 4)

    def test_missing_data_still_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            result = DataQualityDecisionRobustness(root).run()
            self.assertEqual(result["status"], "PASS")

    def test_outputs_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            DataQualityDecisionRobustness(root).run()
            rt = root / "runtime/decision_robustness_v31_v35"
            self.assertTrue(
                (rt / "latest_robustness_report.json").exists()
            )
            self.assertTrue(
                (rt / "daily_robustness_summary.json").exists()
            )

    def test_live_write_off(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = DataQualityDecisionRobustness(root).run()
            self.assertFalse(result["etrade_live_write_enabled"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
