from __future__ import annotations

import tempfile
import unittest
from http import HTTPStatus
from pathlib import Path

from operator_dashboard import create_app


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "operator_dashboard/templates").mkdir(
            parents=True, exist_ok=True
        )
        (self.root / "operator_dashboard/static").mkdir(
            parents=True, exist_ok=True
        )
        (self.root / "operator_dashboard/templates/index.html").write_text(
            "AI STOCK BOT CONTROL CENTER",
            encoding="utf-8",
        )
        (self.root / "operator_dashboard/static/dashboard.css").write_text(
            "",
            encoding="utf-8",
        )
        (self.root / "operator_dashboard/static/dashboard.js").write_text(
            "",
            encoding="utf-8",
        )
        self.app = create_app(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_health(self):
        data = self.app.health_payload()
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["paper_broker"], "ALPACA")
        self.assertEqual(data["live_broker"], "ETRADE")
        self.assertFalse(data["live_write_enabled"])

    def test_status_safety(self):
        data = self.app.status_payload()
        self.assertFalse(data["safety"]["live_write_enabled"])
        self.assertFalse(data["safety"]["multi_account_enabled"])

    def test_start_is_paper_only(self):
        status, data = self.app.action_payload("START")
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(data["operator"]["runtime_status"], "RUNNING")
        self.assertEqual(data["operator"]["requested_mode"], "PAPER")
        self.assertFalse(data["operator"]["live_write_enabled"])

    def test_emergency_stop(self):
        self.app.action_payload("START")
        status, data = self.app.action_payload("EMERGENCY_STOP")
        self.assertEqual(status, HTTPStatus.OK)
        self.assertTrue(data["operator"]["emergency_stop"])
        self.assertEqual(data["operator"]["runtime_status"], "STOPPED")

    def test_invalid_action_rejected(self):
        status, _ = self.app.action_payload("ENABLE_LIVE")
        self.assertEqual(status, HTTPStatus.BAD_REQUEST)

    def test_index_file(self):
        text = self.app._text_file(
            "operator_dashboard/templates/index.html"
        )
        self.assertIn("AI STOCK BOT CONTROL CENTER", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
