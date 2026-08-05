from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace

from automation_watchdog.service import AutomationWatchdog

class Tests(unittest.TestCase):
    def policy(self, root: Path, max_restarts=3):
        path = root / "policy.json"
        path.write_text(json.dumps({
            "controller_profile": "profile.json",
            "poll_interval_seconds": 1,
            "maximum_restart_attempts": max_restarts,
            "restart_backoff_seconds": 1,
            "stale_lock_seconds": 10,
            "heartbeat_timeout_seconds": 10,
            "crash_window_seconds": 600,
            "stop_when_market_closed": True,
            "actual_submission_allowed": False,
        }), encoding="utf-8")
        return path

    def test_successful_controller_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = AutomationWatchdog(
                root, clock_provider=lambda: {"is_open": True}
            ).run(
                policy_path=self.policy(root),
                max_watch_cycles=1,
                controller_runner=lambda command: SimpleNamespace(
                    returncode=0, stdout="PASS", stderr=""
                ),
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["restart_count"], 0)

    def test_failed_controller_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = AutomationWatchdog(
                root, clock_provider=lambda: {"is_open": True}
            ).run(
                policy_path=self.policy(root),
                max_watch_cycles=1,
                controller_runner=lambda command: SimpleNamespace(
                    returncode=1, stdout="", stderr="failure"
                ),
            )
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["restart_count"], 1)

    def test_market_closed_idle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = AutomationWatchdog(
                root, clock_provider=lambda: {"is_open": False}
            ).run(
                policy_path=self.policy(root),
                max_watch_cycles=1,
                controller_runner=lambda command: None,
            )
            self.assertEqual(result["status"], "IDLE")

    def test_submission_policy_hard_block(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "policy.json"
            path.write_text(json.dumps({
                "actual_submission_allowed": True
            }), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                AutomationWatchdog(
                    root, clock_provider=lambda: {"is_open": True}
                ).run(
                    policy_path=path,
                    max_watch_cycles=1,
                    controller_runner=lambda command: None,
                )

    def test_zero_orders_contract(self):
        import inspect
        source = inspect.getsource(AutomationWatchdog.run)
        self.assertIn('"actual_paper_orders_submitted": 0', source)
        self.assertIn('"actual_live_orders_submitted": 0', source)

if __name__ == "__main__":
    unittest.main(verbosity=2)
