from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from paper_command_center.commands import (
    create_command_plan,
)
from paper_command_center.service import (
    PaperCommandCenterCertificationService,
)


class Tests(unittest.TestCase):
    def test_dry_run_plan(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plan = create_command_plan(
                action="START",
                requested_by="TEST",
                reason="test",
                output_path=root / "plan.json",
                audit_path=root / "audit.jsonl",
            )
            self.assertEqual(
                plan["mode"],
                "DRY_RUN_ONLY",
            )
            self.assertEqual(
                plan["execution_status"],
                "NOT_EXECUTED",
            )
            self.assertFalse(
                plan["safety"][
                    "process_execution_enabled"
                ]
            )

    def test_invalid_action_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaises(ValueError):
                create_command_plan(
                    action="DELETE_ALL",
                    requested_by="TEST",
                    reason="",
                    output_path=root / "plan.json",
                    audit_path=root / "audit.jsonl",
                )

    def test_certification(self):
        with tempfile.TemporaryDirectory() as d:
            result = (
                PaperCommandCenterCertificationService()
                .evaluate(output_dir=Path(d))
            )
            self.assertEqual(
                result["status"],
                "PASS",
            )

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as d:
            result = (
                PaperCommandCenterCertificationService()
                .evaluate(output_dir=Path(d))
            )
            self.assertFalse(
                result[
                    "actual_process_started"
                ]
            )
            self.assertFalse(
                result[
                    "actual_broker_write_performed"
                ]
            )
            self.assertEqual(
                result[
                    "actual_paper_orders_submitted"
                ],
                0,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
