import json
import tempfile
import unittest
from pathlib import Path

from paper_observability import PaperObservabilityIntelligence


class Tests(unittest.TestCase):
    def setup_root(self, root: Path):
        candidate = (
            root
            / "release/v14001_15000_paper_autonomous_execution/"
              "actual/latest_paper_execution_cycle.json"
        )
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text(json.dumps({
            "selected_candidate": {
                "symbol": "AAPL",
                "side": "buy",
                "confidence": 0.91,
                "consensus_score": 0.95,
                "reward_risk": 2.0
            }
        }), encoding="utf-8")

        guard = (
            root
            / "runtime/paper_autonomous_daily_session/"
              "latest_shadow_guard_decision.json"
        )
        guard.parent.mkdir(parents=True, exist_ok=True)
        guard.write_text(json.dumps({
            "action": "SHADOW_BLOCK",
            "enforced": False,
            "would_allow_order": False,
            "quality_score": 0.8,
            "issues": [{"code": "DAILY_ORDER_LIMIT"}],
            "warnings": []
        }), encoding="utf-8")

        session = (
            root
            / "runtime/paper_autonomous_daily_session/"
              "latest_status.json"
        )
        session.write_text(json.dumps({
            "stage": "DAILY_ORDER_LIMIT_REACHED_MONITORING",
            "status": "PASS",
            "today_order_count": 1,
            "maximum_daily_orders": 1
        }), encoding="utf-8")

    def test_read_only_report_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = PaperObservabilityIntelligence(root).run()
            self.assertEqual(result["status"], "PASS")
            self.assertFalse(result["broker_write_performed"])
            self.assertEqual(
                result["selected_candidate"]["symbol"], "AAPL"
            )

    def test_explanation_contains_reasons(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = PaperObservabilityIntelligence(root).run()
            reasons = result["explanation"]["positive_reasons"]
            self.assertIn("HIGH_CONFIDENCE", reasons)
            self.assertIn("STRONG_CONSENSUS", reasons)

    def test_journal_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            PaperObservabilityIntelligence(root).run()
            self.assertTrue((
                root
                / "runtime/paper_observability_intelligence/"
                  "trade_journal.jsonl"
            ).exists())

    def test_daily_summary_written(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            PaperObservabilityIntelligence(root).run()
            self.assertTrue((
                root
                / "runtime/paper_observability_intelligence/"
                  "daily_summary.json"
            ).exists())

    def test_live_write_always_off(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            result = PaperObservabilityIntelligence(root).run()
            self.assertFalse(
                result["etrade_live_write_enabled"]
            )

    def test_missing_sources_still_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            result = PaperObservabilityIntelligence(root).run()
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(
                result["selected_candidate"]["side"], "HOLD"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
