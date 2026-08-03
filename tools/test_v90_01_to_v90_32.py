import unittest
from dashboard_analytics_v3.render import badge, bar, render
from dashboard_analytics_v3.analytics import collect
from pathlib import Path
import tempfile

class Tests(unittest.TestCase):
 def test_badge_good(self): self.assertIn("good",badge("PASS"))
 def test_badge_warning(self): self.assertIn("warn",badge("PENDING"))
 def test_bar(self): self.assertIn("50.00%",bar(50))
 def test_collect_safety(self):
  with tempfile.TemporaryDirectory() as t:
   data=collect(Path(t))
   self.assertTrue(data["paper_only"]); self.assertFalse(data["order_submission_enabled"])
 def test_collect_validation_default(self):
  with tempfile.TemporaryDirectory() as t:
   self.assertEqual(collect(Path(t))["validation_progress"]["remaining_days"],3)
 def test_render_title(self):
  with tempfile.TemporaryDirectory() as t:
   self.assertIn("Dashboard Analytics v3",render(collect(Path(t))))
 def test_render_strategy_table(self):
  with tempfile.TemporaryDirectory() as t:
   self.assertIn("Strategy Performance",render(collect(Path(t))))
 def test_render_risk(self):
  with tempfile.TemporaryDirectory() as t:
   self.assertIn("Portfolio Risk Gate",render(collect(Path(t))))
 def test_render_validation(self):
  with tempfile.TemporaryDirectory() as t:
   self.assertIn("Final Validation Progress",render(collect(Path(t))))
 def test_render_api_link(self):
  with tempfile.TemporaryDirectory() as t:
   self.assertIn("/api/analytics",render(collect(Path(t))))
if __name__=="__main__": unittest.main()
