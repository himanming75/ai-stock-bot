from __future__ import annotations
import inspect
import tempfile
import unittest
from pathlib import Path

from fundamental_sector_options_intelligence.io import write_json
from fundamental_sector_options_intelligence.service import (
    FundamentalSectorOptionsIntelligenceService,
)


class Tests(unittest.TestCase):
    def inputs(self, root: Path):
        fundamentals = root / "fundamentals.json"
        sectors = root / "sectors.json"
        options = root / "options.json"

        write_json(
            fundamentals,
            {
                "items": [
                    {
                        "symbol": "AAA",
                        "sector": "Technology",
                        "pe": 18,
                        "forward_pe": 16,
                        "peg": 1.2,
                        "price_sales": 3,
                        "price_book": 4,
                        "ev_ebitda": 12,
                        "roe": 0.24,
                        "roa": 0.11,
                        "gross_margin": 0.62,
                        "operating_margin": 0.25,
                        "net_margin": 0.20,
                        "debt_equity": 0.4,
                        "current_ratio": 1.8,
                        "quick_ratio": 1.5,
                        "revenue_growth": 0.15,
                        "eps_growth": 0.20,
                        "fcf_margin": 0.18,
                        "dividend_yield": 0.01,
                        "buyback_yield": 0.02,
                    }
                ]
            },
        )
        write_json(
            sectors,
            {
                "items": [
                    {
                        "sector": "Technology",
                        "return_1m": 0.04,
                        "return_3m": 0.08,
                        "return_6m": 0.14,
                        "relative_strength": 0.30,
                        "breadth": 0.65,
                        "earnings_revision": 0.20,
                        "fund_flow": 0.15,
                        "volatility": 0.22,
                    }
                ]
            },
        )
        write_json(
            options,
            {
                "items": [
                    {
                        "symbol": "AAA",
                        "put_call_ratio": 0.75,
                        "iv_rank": 0.40,
                        "iv_percentile": 0.45,
                        "call_put_open_interest_ratio": 1.4,
                        "skew": 0.10,
                        "gamma_exposure": 0.20,
                        "expected_move": 0.03,
                        "max_pain_distance": 0.01,
                        "unusual_flow_score": 0.25,
                    }
                ]
            },
        )
        return fundamentals, sectors, options

    def evaluate(self, root):
        fundamentals, sectors, options = self.inputs(root)
        return FundamentalSectorOptionsIntelligenceService().evaluate(
            fundamentals_path=fundamentals,
            sectors_path=sectors,
            options_path=options,
            output_dir=root / "out",
        )

    def test_profile_created(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory))
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["symbol_profile_count"], 1)

    def test_sector_rank_created(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory))
            self.assertEqual(result["sector_ranking"][0]["sector_rank"], 1)

    def test_missing_inputs_block(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = FundamentalSectorOptionsIntelligenceService().evaluate(
                fundamentals_path=root / "f.json",
                sectors_path=root / "s.json",
                options_path=root / "o.json",
                output_dir=root / "out",
            )
            self.assertEqual(result["status"], "BLOCKED")

    def test_outputs_created(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.evaluate(root)
            self.assertTrue(
                (root / "out/fundamental_sector_options_dataset.csv").exists()
            )
            self.assertTrue(
                (root / "out/fundamental_sector_options_ledger.jsonl").exists()
            )

    def test_zero_order_contract(self):
        source = inspect.getsource(
            FundamentalSectorOptionsIntelligenceService
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
