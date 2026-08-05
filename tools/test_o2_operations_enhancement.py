from __future__ import annotations
import os
import tempfile
import unittest
from pathlib import Path

from operations.history import performance_summary
from operations.notifications import (
    NotificationCenter,
    NotificationConfig,
)
from operations.recovery import build_recovery_snapshot
from operations.scheduler_monitor import scheduler_status
from operations.watchdog import evaluate_watchdog


class Tests(unittest.TestCase):
    def test_notifications_default_disabled(self):
        config = NotificationConfig(
            enabled=False,
            discord_webhook_url="",
            slack_webhook_url="",
            telegram_bot_token="",
            telegram_chat_id="",
            smtp_host="",
            smtp_port=587,
            smtp_username="",
            smtp_password="",
            email_from="",
            email_to="",
        )
        result = NotificationCenter(config).send("x", "y")
        self.assertEqual(result["status"], "DISABLED")

    def test_watchdog_no_runtime_is_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checkpoint = (
                root / "release/p4_autonomous_paper_runtime/actual/"
                       "runtime_checkpoint.json"
            )
            checkpoint.parent.mkdir(parents=True, exist_ok=True)
            checkpoint.write_text("{}", encoding="utf-8")
            result = evaluate_watchdog(root)
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["automatic_order_replay_enabled"])

    def test_scheduler_requires_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
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
            result = scheduler_status(root)
        self.assertEqual(result["status"], "PASS")

    def test_recovery_never_auto_replays_orders(self):
        with tempfile.TemporaryDirectory() as directory:
            result = build_recovery_snapshot(Path(directory))
        self.assertFalse(result["automatic_order_replay_enabled"])
        self.assertFalse(result["safe_to_auto_resume"])

    def test_empty_performance_is_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            result = performance_summary(Path(directory))
        self.assertEqual(result["realized_pnl"], "0")
        self.assertEqual(result["win_rate"], 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
