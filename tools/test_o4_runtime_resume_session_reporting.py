from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from operations.daily_reporting import export_daily_report
from operations.graceful_shutdown import write_shutdown_marker
from operations.operator_checklist import build_operator_checklist
from operations.session_rotation import rotate_session


def prepare(root: Path) -> None:
    policy = (
        root / "release/p4_autonomous_paper_runtime/config/"
               "p4_runtime_policy.json"
    )
    policy.parent.mkdir(parents=True, exist_ok=True)
    policy.write_text(
        '{"cycle_interval_seconds":60,'
        '"maximum_cycles_per_session":390,'
        '"require_market_open":true,'
        '"fail_closed":true}',
        encoding="utf-8",
    )
    checkpoint = (
        root / "release/p4_autonomous_paper_runtime/actual/"
               "runtime_checkpoint.json"
    )
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.write_text('{"state":"P4_CYCLE_COMPLETE"}', encoding="utf-8")
    kill = (
        root / "release/p1_broker_consolidation/actual/"
               "kill_switch.json"
    )
    kill.parent.mkdir(parents=True, exist_ok=True)
    kill.write_text(
        '{"kill_switch_active":true,"reason":"TEST"}',
        encoding="utf-8",
    )


class Tests(unittest.TestCase):
    def test_session_rotation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = rotate_session(root, trading_day="2026-08-05", reason="A")
            second = rotate_session(root, trading_day="2026-08-05", reason="B")
        self.assertNotEqual(first["session_id"], second["session_id"])
        self.assertFalse(second["automatic_order_replay_enabled"])

    def test_shutdown_marker_blocks_orders(self):
        with tempfile.TemporaryDirectory() as directory:
            result = write_shutdown_marker(
                Path(directory),
                runtime_id="x",
                reason="test",
                last_cycle_number=3,
            )
        self.assertFalse(result["new_order_submission_allowed"])

    def test_daily_report_exports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare(root)
            result = export_daily_report(
                root,
                trading_day="2026-08-05",
            )
            self.assertTrue(Path(result["json_path"]).exists())
            self.assertTrue(Path(result["csv_path"]).exists())

    def test_operator_checklist_never_auto_resumes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare(root)
            result = build_operator_checklist(root)
        self.assertFalse(result["automatic_resume_enabled"])
        self.assertFalse(result["automatic_order_replay_enabled"])
        self.assertFalse(result["all_complete"])

    def test_zero_orders(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepare(root)
            result = export_daily_report(root)
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
