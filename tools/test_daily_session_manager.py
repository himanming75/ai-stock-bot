from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from daily_session_manager.service import (
    DailySessionManager,
)


class Tests(unittest.TestCase):
    def policy(self, root: Path):
        path = root / "policy.json"
        path.write_text(
            json.dumps(
                {
                    "session_timezone": "America/New_York",
                    "launch_watchdog_when_market_open": True,
                    "stop_after_market_close": True,
                    "allow_weekend_start": True,
                    "startup_delay_seconds": 0,
                    "maximum_daily_launches": 1,
                    "actual_submission_allowed": False,
                    "watchdog_script": "watchdog.ps1",
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_open_market_ready_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = DailySessionManager(
                root,
                clock_provider=lambda: {"is_open": True},
            ).evaluate(
                policy_path=self.policy(root),
                execute_watchdog=False,
            )
            self.assertEqual(
                result["action"],
                "WATCHDOG_LAUNCH_READY",
            )
            self.assertFalse(
                result["watchdog_launched"]
            )

    def test_closed_market_session_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = DailySessionManager(
                root,
                clock_provider=lambda: {"is_open": False},
            ).evaluate(
                policy_path=self.policy(root),
                execute_watchdog=False,
            )
            self.assertEqual(
                result["action"],
                "SESSION_CLOSED",
            )

    def test_watchdog_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "watchdog.ps1").write_text(
                "Write-Host PASS",
                encoding="utf-8",
            )

            def runner(*args, **kwargs):
                return SimpleNamespace(
                    returncode=0,
                    stdout="PASS",
                    stderr="",
                )

            result = DailySessionManager(
                root,
                clock_provider=lambda: {"is_open": True},
                process_runner=runner,
            ).evaluate(
                policy_path=self.policy(root),
                execute_watchdog=True,
            )
            self.assertTrue(
                result["watchdog_launched"]
            )
            self.assertEqual(
                result["watchdog_exit_code"],
                0,
            )

    def test_submission_policy_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "policy.json"
            path.write_text(
                json.dumps(
                    {
                        "actual_submission_allowed": True
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(RuntimeError):
                DailySessionManager(
                    root,
                    clock_provider=lambda: {
                        "is_open": True
                    },
                ).evaluate(
                    policy_path=path,
                    execute_watchdog=False,
                )

    def test_zero_orders_contract(self):
        import inspect

        source = inspect.getsource(
            DailySessionManager.evaluate
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
