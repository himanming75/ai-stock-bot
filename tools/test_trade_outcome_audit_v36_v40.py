import json
import tempfile
import unittest
from pathlib import Path

from trade_outcome_audit_v36_v40 import TradeOutcomeAuditDataPack


class Tests(unittest.TestCase):
    def setup_root(self, root: Path):
        v4 = root / "runtime/closed_trade_calibration_v4/latest_calibration_report.json"
        v4.parent.mkdir(parents=True, exist_ok=True)
        v4.write_text(json.dumps({
            "linked_outcomes": [
                {
                    "trade_id": "T1",
                    "symbol": "AAPL",
                    "side": "BUY",
                    "entry_time": "2026-08-06T14:00:00+00:00",
                    "exit_time": "2026-08-06T15:00:00+00:00",
                    "entry_price": 300,
                    "exit_price": 305,
                    "quantity": 1,
                    "realized_pl": 5,
                    "realized_return": 0.0167,
                    "mfe": 7,
                    "mae": -2,
                    "post_exit_1h_return": 0.002,
                    "candidate": {
                        "confidence": 0.91,
                        "consensus_score": 0.95,
                        "reward_risk": 2.0,
                        "guard_action": "SHADOW_ALLOW"
                    }
                }
            ]
        }), encoding="utf-8")

        execution = root / "runtime/execution_quality_v26_v30/latest_execution_quality_report.json"
        execution.parent.mkdir(parents=True, exist_ok=True)
        execution.write_text(json.dumps({
            "v26_entry_timing_quality": {
                "timing_score": 0.8,
                "timing_state": "STRONG_WINDOW"
            },
            "v27_slippage_liquidity_risk": {
                "slippage_risk": "LOW",
                "estimated_slippage_bps": 3,
                "liquidity_score": 0.85
            },
            "v28_adaptive_notional_recommendation": {
                "suggested_notional": 75
            }
        }), encoding="utf-8")

        brain = root / "runtime/ai_brain_v4/latest_ai_brain_report.json"
        brain.parent.mkdir(parents=True, exist_ok=True)
        brain.write_text(json.dumps({
            "multi_factor_ranking": {
                "top_candidate": {
                    "symbol": "AAPL"
                }
            },
            "explainable_final_decision": {
                "brain_score": 0.82
            }
        }), encoding="utf-8")

    def test_run_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = TradeOutcomeAuditDataPack(root).run()
            self.assertEqual(result["status"], "PASS")
            self.assertFalse(result["broker_write_performed"])

    def test_lifecycle_normalized(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = TradeOutcomeAuditDataPack(
                root
            ).v36_trade_lifecycle_normalizer()
            self.assertEqual(result["trade_count"], 1)
            self.assertEqual(
                result["trades"][0]["symbol"], "AAPL"
            )

    def test_mfe_mae_uses_real_input_only(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = TradeOutcomeAuditDataPack(
                root
            ).v37_mfe_mae_analyzer()
            self.assertEqual(
                result["path_data_available_count"], 1
            )
            self.assertFalse(result["fabricated_path_data"])

    def test_execution_record_no_write(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = TradeOutcomeAuditDataPack(
                root
            ).v39_execution_quality_record()
            self.assertFalse(
                result["record"]["broker_write_performed"]
            )
            self.assertEqual(result["order_effect"], "NONE")

    def test_missing_data_still_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            result = TradeOutcomeAuditDataPack(root).run()
            self.assertEqual(result["status"], "PASS")

    def test_outputs_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            TradeOutcomeAuditDataPack(root).run()
            rt = root / "runtime/trade_outcome_audit_v36_v40"
            self.assertTrue(
                (rt / "latest_trade_audit_report.json").exists()
            )
            self.assertTrue(
                (rt / "daily_trade_audit_dataset.json").exists()
            )

    def test_live_write_off(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = TradeOutcomeAuditDataPack(root).run()
            self.assertFalse(result["etrade_live_write_enabled"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
