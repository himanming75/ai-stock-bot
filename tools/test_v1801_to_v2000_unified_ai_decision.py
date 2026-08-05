from __future__ import annotations
import inspect
import tempfile
import unittest
from pathlib import Path

from unified_ai_decision_reasoning.io import write_json
from unified_ai_decision_reasoning.service import (
    UnifiedAIDecisionReasoningService,
)


class Tests(unittest.TestCase):
    def inputs(self, root: Path, include_ensemble=True):
        ensemble = root / "ensemble.json"
        news = root / "news.json"
        fundamental = root / "fundamental.json"

        write_json(
            ensemble,
            {
                "ranked_ensemble_results": (
                    [
                        {
                            "symbol": "QQQ",
                            "ensemble_score": 55,
                            "confidence": 80,
                            "disagreement": 0.15,
                        }
                    ]
                    if include_ensemble else []
                )
            },
        )
        write_json(
            news,
            {
                "symbol_profiles": [
                    {
                        "symbol": "QQQ",
                        "intelligence_score": 0.25,
                        "confidence": 70,
                        "event_risk": 0.10,
                    }
                ]
            },
        )
        write_json(
            fundamental,
            {
                "symbol_profiles": [
                    {
                        "symbol": "QQQ",
                        "fundamental_score": 0.50,
                        "sector_score": 0.35,
                        "options_score": 0.30,
                        "options_event_risk": 0.25,
                        "confidence": 75,
                    }
                ]
            },
        )
        return ensemble, news, fundamental

    def evaluate(self, root, include_ensemble=True):
        ensemble, news, fundamental = self.inputs(
            root,
            include_ensemble=include_ensemble,
        )
        return UnifiedAIDecisionReasoningService().evaluate(
            ensemble_path=ensemble,
            news_path=news,
            fundamental_path=fundamental,
            output_dir=root / "out",
        )

    def test_complete_input_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory))
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["symbol_decision_count"], 1)

    def test_partial_input_supported(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(
                Path(directory),
                include_ensemble=False,
            )
            self.assertEqual(result["status"], "PARTIAL_INPUT")
            self.assertIn(
                "technical",
                result["decisions"][0]["missing_components"],
            )

    def test_reasoning_created(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory))
            self.assertTrue(
                result["decisions"][0]["reasoning"]["summary"]
            )

    def test_outputs_created(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.evaluate(root)
            self.assertTrue(
                (root / "out/explainable_decision_reports.json").exists()
            )
            self.assertTrue(
                (root / "out/unified_ai_decision_ledger.jsonl").exists()
            )

    def test_zero_order_contract(self):
        source = inspect.getsource(
            UnifiedAIDecisionReasoningService
        )
        self.assertIn(
            '"actual_broker_write_performed": False',
            source,
        )
        self.assertIn(
            '"actual_paper_orders_submitted": 0',
            source,
        )
        self.assertIn(
            '"actual_live_orders_submitted": 0',
            source,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
