from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from paper_daily_session.runner import PaperDailySessionRunner


class FakeAccount:
    status = "ACTIVE"
    trading_blocked = False


class FakeClock:
    is_open = True
    timestamp = None
    next_open = None
    next_close = None


class FakeClient:
    def get_account(self):
        return FakeAccount()

    def get_clock(self):
        return FakeClock()

    def get_orders(self, filter=None):
        return []


class TestRunner(PaperDailySessionRunner):
    def _client(self):
        return FakeClient()

    def _today_orders(self, client):
        return []

    def _clock_data(self, client):
        return {
            "market_open": True,
            "clock_timestamp": "",
            "next_open": "",
            "next_close": "",
            "minutes_to_close": 120,
        }


class Tests(unittest.TestCase):
    def setup_root(self, root: Path) -> None:
        (root / "RUN_ONE_PAPER_VALIDATION_ORDER_V14001_TO_V15000.ps1").write_text(
            'Write-Host "PASS"', encoding="utf-8"
        )

    def env(self):
        return patch.dict(os.environ, {
            "APCA_API_KEY_ID": "paper-key",
            "APCA_API_SECRET_KEY": "paper-secret",
            "LIVE_TRADING_ENABLED": "false",
            "ETRADE_LIVE_WRITE_ENABLED": "false",
            "ETRADE_LIVE_SUBMISSION_ENABLED": "false",
        }, clear=True)

    def test_dry_run_pass(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            with self.env():
                result = TestRunner(root, dry_run=True).run()
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["stage"], "DRY_RUN_COMPLETED")

    def test_live_flag_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            with patch.dict(os.environ, {
                "APCA_API_KEY_ID": "x",
                "APCA_API_SECRET_KEY": "y",
                "LIVE_TRADING_ENABLED": "true",
            }, clear=True):
                result = TestRunner(root, dry_run=True).run()
            self.assertEqual(result["status"], "BLOCKED")

    def test_daily_order_range_contract(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            # _validate_environment requires the controlled order script
            # and Paper credentials, but it performs no broker call.
            (root / "RUN_ONE_PAPER_VALIDATION_ORDER_V14001_TO_V15000.ps1").write_text(
                "# test placeholder",
                encoding="utf-8",
            )

            old_key = os.environ.get("APCA_API_KEY_ID")
            old_secret = os.environ.get("APCA_API_SECRET_KEY")
            old_live = os.environ.get("LIVE_TRADING_ENABLED")
            old_etrade_write = os.environ.get("ETRADE_LIVE_WRITE_ENABLED")
            old_etrade_submit = os.environ.get("ETRADE_LIVE_SUBMISSION_ENABLED")

            try:
                os.environ["APCA_API_KEY_ID"] = "test-paper-key"
                os.environ["APCA_API_SECRET_KEY"] = "test-paper-secret"
                os.environ["LIVE_TRADING_ENABLED"] = "false"
                os.environ["ETRADE_LIVE_WRITE_ENABLED"] = "false"
                os.environ["ETRADE_LIVE_SUBMISSION_ENABLED"] = "false"

                valid = PaperDailySessionRunner(
                    root,
                    maximum_daily_orders=15,
                    dry_run=True,
                )
                valid._validate_environment()

                invalid = PaperDailySessionRunner(
                    root,
                    maximum_daily_orders=51,
                    dry_run=True,
                )
                with self.assertRaisesRegex(
                    RuntimeError,
                    "MAXIMUM_DAILY_ORDERS_INVALID",
                ):
                    invalid._validate_environment()
            finally:
                env_values = {
                    "APCA_API_KEY_ID": old_key,
                    "APCA_API_SECRET_KEY": old_secret,
                    "LIVE_TRADING_ENABLED": old_live,
                    "ETRADE_LIVE_WRITE_ENABLED": old_etrade_write,
                    "ETRADE_LIVE_SUBMISSION_ENABLED": old_etrade_submit,
                }
                for name, value in env_values.items():
                    if value is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = value

    def test_notional_contract(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            self.setup_root(root)
            with self.env():
                result = TestRunner(
                    root, maximum_order_notional=101, dry_run=True
                ).run()
            self.assertEqual(result["status"], "BLOCKED")

    def test_duplicate_session_lock(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            runner = TestRunner(root, dry_run=True)
            runner.lock_path.parent.mkdir(parents=True, exist_ok=True)
            runner.lock_path.write_text("locked", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                runner._acquire_lock()

    def test_safety_state(self):
        with tempfile.TemporaryDirectory() as d:
            runner = TestRunner(Path(d), dry_run=True)
            state = runner._status("TEST")
            self.assertTrue(state["paper_only"])
            self.assertFalse(state["etrade_live_write_enabled"])
            self.assertEqual(state["live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
