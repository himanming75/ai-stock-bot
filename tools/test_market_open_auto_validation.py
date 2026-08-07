from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from market_open_validation.runner import (
    AutoValidationRunner,
    resolve_unique,
)


class FakeAccount:
    status = "ACTIVE"
    account_number = "PA123456"
    equity = "100000"
    buying_power = "200000"
    account_blocked = False
    trading_blocked = False
    transfers_blocked = False


class FakeClock:
    is_open = True
    timestamp = "2026-08-06T13:30:00Z"
    next_open = "2026-08-07T13:30:00Z"
    next_close = "2026-08-06T20:00:00Z"


class FakeClient:
    def get_account(self):
        return FakeAccount()

    def get_clock(self):
        return FakeClock()


class TestRunner(AutoValidationRunner):
    def _trading_client(self):
        return FakeClient()


class Tests(unittest.TestCase):
    def _scripts(self, root: Path) -> None:
        for name in (
            "RUN_V14001_TO_V15000_PREFLIGHT.ps1",
            "ARM_PAPER_ONLY_V14001_TO_V15000.ps1",
            "RUN_ONE_PAPER_VALIDATION_ORDER_V14001_TO_V15000.ps1",
        ):
            (root / name).write_text(
                'Write-Host "PASS"',
                encoding="utf-8",
            )

    def test_dry_run_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._scripts(root)
            with patch.dict(os.environ, {
                "APCA_API_KEY_ID": "paper-key",
                "APCA_API_SECRET_KEY": "paper-secret",
            }, clear=True):
                result = TestRunner(
                    root, poll_seconds=10, timeout_minutes=1, dry_run=True
                ).run()
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["actual_live_orders_submitted"], 0)

    def test_missing_credentials_block(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._scripts(root)
            with patch.dict(os.environ, {}, clear=True):
                result = TestRunner(root, dry_run=True).run()
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("PAPER_CREDENTIALS_MISSING", result["reason"])

    def test_live_env_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self._scripts(root)
            with patch.dict(os.environ, {
                "APCA_API_KEY_ID": "paper-key",
                "APCA_API_SECRET_KEY": "paper-secret",
                "LIVE_TRADING_ENABLED": "true",
            }, clear=True):
                result = TestRunner(root, dry_run=True).run()
            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("LIVE_WRITE_ENV_MUST_BE_OFF", result["reason"])

    def test_duplicate_script_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "RUN_ONE_PAPER_VALIDATION_ORDER_A.ps1").write_text("")
            (root / "RUN_ONE_PAPER_VALIDATION_ORDER_B.ps1").write_text("")
            with self.assertRaises(RuntimeError):
                resolve_unique(
                    root,
                    ["RUN_ONE_*PAPER*VALIDATION*ORDER*.ps1"],
                )

    def test_lock_blocks_second_runner(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            runner = TestRunner(root, dry_run=True)
            runner.lock_path.parent.mkdir(parents=True, exist_ok=True)
            runner.lock_path.write_text("locked", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                runner._acquire_lock()

    def test_state_hardcodes_safety(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            runner = TestRunner(root, dry_run=True)
            state = runner._state("TEST")
            self.assertTrue(state["paper_only"])
            self.assertFalse(state["etrade_live_write_enabled"])
            self.assertEqual(state["maximum_validation_orders"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
