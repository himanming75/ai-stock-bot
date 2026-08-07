from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from operator_dashboard import create_app


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

        report = self.root / (
            "release/v11001_12000_multi_timeframe_ai/actual/"
            "multi_timeframe_ai_report_bilingual.json"
        )
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps({
            "analyses": [{
                "symbol": "AAPL",
                "action": "BUY",
                "confidence_calibration": {
                    "calibrated_confidence": 0.91
                },
                "market_regime_2": "STRONG_BULL",
                "reward_risk": 2.1,
            }]
        }), encoding="utf-8")

        profile = self.root / (
            "release/v14001_15000_paper_autonomous_execution/config/"
            "paper_execution_profile.json"
        )
        profile.parent.mkdir(parents=True, exist_ok=True)
        profile.write_text(json.dumps({
            "allowed_symbols": ["AAPL", "MSFT"]
        }), encoding="utf-8")

        self.app = create_app(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_ai_candidates(self):
        payload = self.app.status_payload()
        rows = payload["operation_console"]["ai_candidates"]
        self.assertEqual(rows[0]["symbol"], "AAPL")
        self.assertEqual(rows[0]["action"], "BUY")

    def test_watchlist(self):
        payload = self.app.status_payload()
        self.assertEqual(
            payload["operation_console"]["watchlist"],
            ["AAPL", "MSFT"],
        )

    def test_stage_idle(self):
        payload = self.app.status_payload()
        self.assertEqual(
            payload["operation_console"]["session_stage"]["stage"],
            "IDLE",
        )

    def test_start_stage_monitoring(self):
        self.app.action_payload("START")
        payload = self.app.status_payload()
        self.assertEqual(
            payload["operation_console"]["session_stage"]["stage"],
            "MONITORING",
        )

    def test_live_write_remains_off(self):
        payload = self.app.status_payload()
        self.assertFalse(payload["safety"]["live_write_enabled"])

    def test_invalid_live_action_blocked(self):
        status, _ = self.app.action_payload("ENABLE_LIVE")
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
