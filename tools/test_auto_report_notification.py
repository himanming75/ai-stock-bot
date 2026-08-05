from __future__ import annotations
from datetime import datetime, timezone
import tempfile
import unittest
from pathlib import Path

from reporting_notification.notifications import (
    NotificationPreviewQueue,
    QuietHoursPolicy,
)


class Tests(unittest.TestCase):
    def test_quiet_hours(self):
        result = QuietHoursPolicy().evaluate(
            observed_at=datetime(2026, 1, 1, 23, 0, tzinfo=timezone.utc)
        )
        self.assertTrue(result["quiet_hours_active"])

    def test_preview_send_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = NotificationPreviewQueue(Path(directory) / "q.jsonl")
            record = queue.enqueue(
                channel="EMAIL",
                alert={
                    "category": "X",
                    "severity": "INFO",
                    "subject": "S",
                    "message": "M",
                },
                quiet_hours={"quiet_hours_active": False},
            )
            self.assertFalse(record["external_send_allowed"])
            with self.assertRaises(RuntimeError):
                queue.send(record["notification_id"])

    def test_duplicate_suppressed(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = NotificationPreviewQueue(Path(directory) / "q.jsonl")
            alert = {
                "category": "X",
                "severity": "INFO",
                "subject": "S",
                "message": "M",
            }
            quiet = {"quiet_hours_active": False}
            queue.enqueue(channel="EMAIL", alert=alert, quiet_hours=quiet)
            second = queue.enqueue(
                channel="EMAIL", alert=alert, quiet_hours=quiet
            )
            self.assertTrue(second["duplicate_suppressed"])

    def test_unsupported_channel(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = NotificationPreviewQueue(Path(directory) / "q.jsonl")
            with self.assertRaises(ValueError):
                queue.enqueue(
                    channel="SMS",
                    alert={},
                    quiet_hours={"quiet_hours_active": False},
                )

    def test_supported_channels(self):
        self.assertEqual(
            NotificationPreviewQueue.SUPPORTED_CHANNELS,
            {"EMAIL", "SLACK", "DISCORD", "TELEGRAM"},
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
