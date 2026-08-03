from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from dashboard_v2.dashboard_state import build_dashboard_state
from dashboard_v2.render import render_html


class DashboardV2Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write_source(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_empty_sources_are_supported(self):
        state = build_dashboard_state(self.root)
        self.assertEqual(state["available_source_count"], 0)
        self.assertEqual(state["dashboard_state"], "DASHBOARD_V2_SAFE")

    def test_available_source_count(self):
        self.write_source(
            "release/v83_77_to_v83_80/actual/"
            "multi_day_paper_validation_result.json",
            {"state": "READY", "status": "PASS", "paper_only": True},
        )
        state = build_dashboard_state(self.root)
        self.assertEqual(state["available_source_count"], 1)

    def test_safety_violation_detected(self):
        self.write_source(
            "release/v83_73_to_v83_76/actual/"
            "paper_autonomous_mode_result.json",
            {"broker_write_enabled": True},
        )
        state = build_dashboard_state(self.root)
        self.assertIn(
            "paper_autonomous:broker_write",
            state["safety_violations"],
        )

    def test_summary_reads_validation_days(self):
        self.write_source(
            "release/v83_77_to_v83_80/actual/"
            "multi_day_paper_validation_result.json",
            {"completed_days": 2, "remaining_days": 1},
        )
        state = build_dashboard_state(self.root)
        self.assertEqual(state["summary"]["validation_completed_days"], 2)

    def test_summary_reads_performance(self):
        self.write_source(
            "release/v83_89_to_v83_96/actual/"
            "performance_production_readiness_result.json",
            {
                "metrics": {"performance_score": 88},
                "risk_gate_passed": True,
            },
        )
        state = build_dashboard_state(self.root)
        self.assertEqual(state["summary"]["performance_score"], 88)

    def test_html_contains_title(self):
        html = render_html(build_dashboard_state(self.root))
        self.assertIn("AI Stock Bot Dashboard v2", html)

    def test_html_escapes_source_values(self):
        self.write_source(
            "release/v83_73_to_v83_76/actual/"
            "paper_autonomous_mode_result.json",
            {"state": "<script>alert(1)</script>"},
        )
        html = render_html(build_dashboard_state(self.root))
        self.assertNotIn("<script>alert(1)</script>", html)

    def test_dashboard_is_read_only(self):
        state = build_dashboard_state(self.root)
        self.assertTrue(state["read_only"])
        self.assertFalse(state["broker_write_enabled"])


if __name__ == "__main__":
    unittest.main()
