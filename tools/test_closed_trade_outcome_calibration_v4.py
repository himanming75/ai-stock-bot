import json
import tempfile
import unittest
from pathlib import Path

from closed_trade_calibration_v4 import ClosedTradeOutcomeCalibration


class Tests(unittest.TestCase):
    def setup_root(self, root: Path):
        journal = (
            root
            / "runtime/paper_observability_intelligence/trade_journal.jsonl"
        )
        journal.parent.mkdir(parents=True, exist_ok=True)
        journal.write_text(json.dumps({
            "observed_at_utc": "2026-08-06T10:00:00+00:00",
            "selected_candidate": {
                "symbol": "AAPL",
                "confidence": 0.91,
                "consensus_score": 0.95,
                "reward_risk": 2.0
            },
            "shadow_guard": {
                "action": "SHADOW_ALLOW",
                "would_allow_order": True
            }
        }) + "\n", encoding="utf-8")

        outcomes = (
            root
            / "runtime/closed_trade_outcomes/closed_trade_outcomes.jsonl"
        )
        outcomes.parent.mkdir(parents=True, exist_ok=True)
        outcomes.write_text(json.dumps({
            "trade_id": "T1",
            "symbol": "AAPL",
            "realized_pl": 10.0,
            "quantity": 1
        }) + "\n", encoding="utf-8")

    def test_run_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = ClosedTradeOutcomeCalibration(root).run()
            self.assertEqual(result["status"], "PASS")
            self.assertFalse(result["broker_write_performed"])

    def test_links_candidate_to_outcome(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            linked = ClosedTradeOutcomeCalibration(root).linked_outcomes()
            self.assertEqual(len(linked), 1)
            self.assertTrue(linked[0]["candidate_linked"])

    def test_calibration_bucket(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            calibration = ClosedTradeOutcomeCalibration(root).calibration()
            self.assertEqual(
                calibration["buckets"]["0.90-1.00"]["sample_count"], 1
            )
            self.assertEqual(
                calibration["buckets"]["0.90-1.00"]["wins"], 1
            )

    def test_no_automatic_changes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = ClosedTradeOutcomeCalibration(root).run()
            self.assertFalse(
                result["confidence_calibration"][
                    "automatic_confidence_adjustment"
                ]
            )
            self.assertFalse(
                result["calibration_recommendation"]["automatic_changes"]
            )

    def test_missing_data_still_passes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            result = ClosedTradeOutcomeCalibration(root).run()
            self.assertEqual(result["status"], "PASS")

    def test_output_files_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            ClosedTradeOutcomeCalibration(root).run()
            runtime = root / "runtime/closed_trade_calibration_v4"
            self.assertTrue(
                (runtime / "latest_calibration_report.json").exists()
            )
            self.assertTrue(
                (runtime / "daily_calibration_summary.json").exists()
            )

    def test_live_write_off(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = ClosedTradeOutcomeCalibration(root).run()
            self.assertFalse(result["etrade_live_write_enabled"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
