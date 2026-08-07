import json
import tempfile
import unittest
from pathlib import Path

from market_regime_v66_v70 import MarketRegimeEnvironmentPack


class Tests(unittest.TestCase):
    def setup_root(self, root: Path):
        brain = (
            root
            / "runtime/ai_brain_v4/"
              "latest_ai_brain_report.json"
        )
        brain.parent.mkdir(parents=True, exist_ok=True)
        brain.write_text(json.dumps({
            "multi_timeframe_ai": {
                "direction": "BULLISH",
                "alignment_score": 0.85,
                "dispersion": 0.15
            }
        }), encoding="utf-8")

        market = (
            root
            / "runtime/market_context_v16_v20/"
              "latest_market_context_report.json"
        )
        market.parent.mkdir(parents=True, exist_ok=True)
        market.write_text(json.dumps({
            "market_context_summary": {
                "market_entry_context": "FAVORABLE_OR_NEUTRAL"
            },
            "v16_market_regime_predictor": {
                "volatility_risk": 0.4
            }
        }), encoding="utf-8")

        execution = (
            root
            / "runtime/execution_quality_v26_v30/"
              "latest_execution_quality_report.json"
        )
        execution.parent.mkdir(parents=True, exist_ok=True)
        execution.write_text(json.dumps({
            "v27_slippage_liquidity_risk": {
                "liquidity_score": 0.8,
                "estimated_slippage_bps": 4.0
            }
        }), encoding="utf-8")

    def test_classifier_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            r = MarketRegimeEnvironmentPack(
                root
            ).v66_market_regime_classifier()
            self.assertEqual(r["status"], "PASS")
            self.assertFalse(r["enforced"])

    def test_snapshot_read_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            r = MarketRegimeEnvironmentPack(
                root
            ).v67_environment_snapshot()
            self.assertFalse(
                r["snapshot"]["broker_write_performed"]
            )

    def test_linker_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            r = MarketRegimeEnvironmentPack(
                root
            ).v68_trade_context_linker()
            self.assertFalse(
                r["existing_trade_ledger_overwritten"]
            )

    def test_regime_dataset_no_auto_weight(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            r = MarketRegimeEnvironmentPack(
                root
            ).v69_regime_performance_dataset()
            self.assertFalse(r["automatic_regime_weighting"])

    def test_health_summary(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            r = MarketRegimeEnvironmentPack(
                root
            ).v70_environment_health_summary()
            self.assertGreaterEqual(r["health_score"], 80)

    def test_missing_data_still_runs(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            r = MarketRegimeEnvironmentPack(root).run()
            self.assertEqual(r["status"], "PASS")

    def test_outputs_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            MarketRegimeEnvironmentPack(root).run()
            rt = root / "runtime/market_regime_v66_v70"
            self.assertTrue(
                (rt / "latest_market_regime_report.json").exists()
            )
            self.assertTrue(
                (rt / "regime_performance_dataset.json").exists()
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
