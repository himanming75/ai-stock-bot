from __future__ import annotations
import json
import tempfile
import unittest
from pathlib import Path

from validation_control.certificate import (
    generate_paper_completion_certificate,
)
from validation_control.status import (
    collect_actual_validation_status,
)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


class Tests(unittest.TestCase):
    def test_missing_results_are_not_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            result = collect_actual_validation_status(Path(directory))
        self.assertFalse(result["paper_complete"])
        self.assertEqual(
            result["next_action"],
            "RUN_P2_P3_ACTUAL_VALIDATION_AFTER_PAPER_ORDER",
        )

    def test_certificate_blocked_when_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            result = generate_paper_completion_certificate(
                Path(directory)
            )
        self.assertFalse(result["eligible"])
        self.assertEqual(result["status"], "BLOCKED")

    def test_complete_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(
                root / "release/p2_actual_paper_execution/actual/"
                       "p2_actual_validation.json",
                {"validated": True, "status": "PASS"},
            )
            write_json(
                root / "release/p3_order_fill_portfolio_sync/actual/"
                       "p3_actual_validation.json",
                {"validated": True, "status": "PASS"},
            )
            write_json(
                root / "release/p4_autonomous_paper_runtime/actual/"
                       "p4_actual_validation.json",
                {"validated": True, "status": "PASS"},
            )
            write_json(
                root / "release/p5_paper_long_run_qualification/actual/"
                       "p5_actual_qualification.json",
                {
                    "actual_paper_long_run_qualified": True,
                    "paper_complete": True,
                    "status": "PASS",
                },
            )
            result = generate_paper_completion_certificate(root)
        self.assertTrue(result["eligible"])
        self.assertTrue(result["paper_complete"])

    def test_status_check_submits_zero_orders(self):
        with tempfile.TemporaryDirectory() as directory:
            result = collect_actual_validation_status(Path(directory))
        self.assertEqual(
            result["actual_paper_orders_submitted_by_status_check"],
            0,
        )
        self.assertEqual(result["actual_live_orders_submitted"], 0)

    def test_live_sequence_starts_after_paper(self):
        with tempfile.TemporaryDirectory() as directory:
            result = collect_actual_validation_status(Path(directory))
        self.assertNotEqual(
            result["next_action"],
            "PAPER_COMPLETE_BEGIN_L2_ACTUAL_LIVE_READ",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
