from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path

from paper_automation_controller.checkpoint import CheckpointStore
from paper_automation_controller.models import AutomationProfile
from paper_automation_controller.service import PaperAutomationController

class TestController(PaperAutomationController):
    def _run_market_pipeline(self, symbols, cycle_number):
        return {
            "cycle_number": cycle_number,
            "symbols_requested": len(symbols),
            "symbols_covered": len(symbols),
            "market_pipeline_status": "PASS",
            "decision_pipeline_status": "BLOCKED",
            "bridge_pipeline_status": "BLOCKED",
        }

    def _run_execution_pipeline(self):
        return {
            "execution_status": "PASS",
            "ticket_status": "PASS",
            "ready_ticket_count": 1,
        }

class Tests(unittest.TestCase):
    def profile(self, root: Path, max_cycles=2):
        path = root / "profile.json"
        path.write_text(json.dumps({
            "name": "READ_ONLY",
            "symbols": ["SPY", "QQQ", "IWM"],
            "interval_seconds": 1,
            "max_cycles": max_cycles,
            "stop_when_market_closed": True,
            "enable_market_pipeline": True,
            "enable_execution_planning": True,
            "enable_order_ticket_generation": True,
            "enable_actual_submission": False,
            "require_submission_approval_token": True,
        }), encoding="utf-8")
        return path

    def test_profile_disables_submission(self):
        profile = AutomationProfile.from_mapping({
            "name": "READ_ONLY",
            "enable_actual_submission": False,
        })
        self.assertFalse(profile.enable_actual_submission)

    def test_controller_cycles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = TestController(
                root, clock_provider=lambda: {"is_open": True}
            ).run(self.profile(root, 2))
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["completed_cycles"], 2)
            self.assertEqual(result["actual_paper_orders_submitted"], 0)

    def test_market_closed_idle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = TestController(
                root, clock_provider=lambda: {"is_open": False}
            ).run(self.profile(root, 1))
            self.assertEqual(result["status"], "IDLE")
            self.assertEqual(result["stopped_reason"], "MARKET_CLOSED")

    def test_checkpoint_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            store = CheckpointStore(path)
            store.save(cycle_number=3, cycle_id="abc", state="COMPLETED", summary={})
            self.assertEqual(store.load()["last_completed_cycle"], 3)

    def test_submission_is_hard_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = root / "profile.json"
            profile.write_text(json.dumps({
                "name": "PAPER_GATED",
                "enable_actual_submission": True,
            }), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                TestController(
                    root, clock_provider=lambda: {"is_open": True}
                ).run(profile)

if __name__ == "__main__":
    unittest.main(verbosity=2)
