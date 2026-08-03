from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from web_ui_v2.app import badge, load_ui_state, render_home, svg_line


class WebUIV2Tests(unittest.TestCase):
    def test_badge(self):
        self.assertIn("good", badge("PASS"))

    def test_svg_empty(self):
        self.assertIn("No curve data", svg_line([]))

    def test_svg_points(self):
        value = svg_line([100, 110, 105])
        self.assertIn("polyline", value)

    def test_load_state_has_safety(self):
        state = load_ui_state()
        self.assertTrue(state["paper_only"])
        self.assertFalse(state["broker_write_enabled"])

    def test_render_title(self):
        page = render_home(load_ui_state())
        self.assertIn("AI Stock Bot Web UI v2", page)

    def test_render_run_button(self):
        page = render_home(load_ui_state())
        self.assertIn("Run Backtest", page)

    def test_render_downloads(self):
        page = render_home(load_ui_state())
        self.assertIn("/download/backtest", page)

    def test_render_safety_text(self):
        page = render_home(load_ui_state())
        self.assertIn("No broker writes", page)


if __name__ == "__main__":
    unittest.main()
