from __future__ import annotations
import inspect
import tempfile
import unittest
from pathlib import Path

from model_validation_backtest.io import write_json
from model_validation_backtest.service import (
    ModelValidationBacktestService,
)


def fixture_rows(count=40):
    rows = []
    for index in range(count):
        score = ((index % 9) - 4) / 10.0
        forward = (
            score * 0.04
            + ((index % 5) - 2) * 0.002
        )
        rows.append({
            "timestamp": f"2026-01-{1 + index // 3:02d}T14:{index % 60:02d}:00Z",
            "symbol": ["SPY", "QQQ", "IWM"][index % 3],
            "final_score": score,
            "confidence": 50 + abs(score) * 80,
            "forward_return": forward,
            "technical_score": score * 0.9,
            "news_score": score * 0.4,
            "fundamental_score": score * 0.6,
            "sector_score": score * 0.3,
            "options_score": score * 0.5,
        })
    return rows


class Tests(unittest.TestCase):
    def evaluate(self, root, count=40):
        path = root / "predictions.json"
        write_json(path, {"items": fixture_rows(count)})
        return ModelValidationBacktestService().evaluate(
            prediction_path=path,
            output_dir=root / "out",
        )

    def test_validation_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory))
            self.assertEqual(result["status"], "PASS")
            self.assertGreater(result["sample_count"], 20)

    def test_threshold_sweep_created(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory))
            self.assertEqual(len(result["threshold_sweep"]), 9)

    def test_small_sample_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.evaluate(Path(directory), count=10)
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn(
                "MINIMUM_SAMPLE_SIZE_NOT_MET",
                result["global_blockers"],
            )

    def test_outputs_created(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.evaluate(root)
            self.assertTrue(
                (root / "out/confidence_calibration.json").exists()
            )
            self.assertTrue(
                (root / "out/model_validation_ledger.jsonl").exists()
            )

    def test_zero_order_contract(self):
        source = inspect.getsource(
            ModelValidationBacktestService
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
