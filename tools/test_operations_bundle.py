from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from operations.jsonlog import JsonEventLogger, redact
from operations.l1_safety import load_live_safety_policy
from operations.monitor import monitor_once
from operations.status_reader import collect_status


class Tests(unittest.TestCase):
    def test_redaction(self):
        value = redact({
            "api_key": "secret",
            "nested": {"secret_key": "hidden"},
        })
        self.assertEqual(value["api_key"], "***REDACTED***")
        self.assertEqual(
            value["nested"]["secret_key"],
            "***REDACTED***",
        )

    def test_logger(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            JsonEventLogger(path).write("TEST")
            self.assertTrue(path.exists())

    def test_missing_status_is_safe(self):
        with tempfile.TemporaryDirectory() as directory:
            status = collect_status(Path(directory))
        self.assertFalse(status["mode"]["live"])
        self.assertFalse(status["qualification"]["paper_complete"])

    def test_monitor_keeps_live_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = monitor_once(root)
        self.assertIn("live_mode_disabled", result["checks"])

    def test_l1_preparation_never_activates_live(self):
        result = load_live_safety_policy().evaluate()
        self.assertFalse(result["live_activation_allowed"])
        self.assertFalse(result["live_network_enabled"])
        self.assertFalse(result["live_write_enabled"])
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
