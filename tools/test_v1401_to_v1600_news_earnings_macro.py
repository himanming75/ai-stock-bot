from __future__ import annotations
import inspect
import tempfile
import unittest
from pathlib import Path

from news_earnings_macro_intelligence.io import write_json
from news_earnings_macro_intelligence.service import (
    NewsEarningsMacroIntelligenceService,
)


class Tests(unittest.TestCase):
    def inputs(self, root: Path):
        news = root / "news.json"
        earnings = root / "earnings.json"
        macro = root / "macro.json"

        write_json(
            news,
            {
                "items": [
                    {
                        "headline": "Company beats estimates and raises guidance",
                        "summary": "Strong growth and record profit",
                        "source": "fixture",
                        "symbols": ["SPY"],
                        "importance": 0.8,
                    }
                ]
            },
        )
        write_json(
            earnings,
            {
                "items": [
                    {
                        "symbol": "SPY",
                        "actual_eps": 2.2,
                        "expected_eps": 2.0,
                        "actual_revenue": 110,
                        "expected_revenue": 100,
                        "guidance_score": 0.5,
                    }
                ]
            },
        )
        write_json(
            macro,
            {
                "items": [
                    {
                        "event_type": "CPI",
                        "actual": 2.8,
                        "expected": 3.0,
                        "importance": 0.9,
                    }
                ]
            },
        )
        return news, earnings, macro

    def evaluate(self, root):
        news, earnings, macro = self.inputs(root)
        return NewsEarningsMacroIntelligenceService().evaluate(
            news_path=news,
            earnings_path=earnings,
            macro_path=macro,
            output_dir=root / "out",
        )

    def test_positive_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory))
            self.assertEqual(result["status"], "PASS")
            self.assertGreater(
                result["symbol_profiles"][0]["intelligence_score"],
                0,
            )

    def test_macro_regime_present(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory))
            self.assertIn(
                result["macro_summary"]["macro_regime"],
                {"RISK_ON", "RISK_OFF", "MIXED_OR_NEUTRAL"},
            )

    def test_missing_inputs_block(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = NewsEarningsMacroIntelligenceService().evaluate(
                news_path=root / "n.json",
                earnings_path=root / "e.json",
                macro_path=root / "m.json",
                output_dir=root / "out",
            )
            self.assertEqual(result["status"], "BLOCKED")

    def test_outputs_created(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.evaluate(root)
            self.assertTrue(
                (root / "out/symbol_intelligence_dataset.csv").exists()
            )
            self.assertTrue(
                (root / "out/news_earnings_macro_ledger.jsonl").exists()
            )

    def test_zero_order_contract(self):
        source = inspect.getsource(
            NewsEarningsMacroIntelligenceService
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
