import unittest
from pathlib import Path

class TestDailyOperationsUI(unittest.TestCase):
    def test_contract(self):
        root=Path(__file__).resolve().parents[1]
        html=(root/"web_controller/static/index.html").read_text(encoding="utf-8")
        js=(root/"web_controller/static/app.js").read_text(encoding="utf-8")
        for text in ("Pre-Market Check","Run Intraday Shadow","Post-Market Report","Recovery Plan","Save Schedule Settings"):
            self.assertIn(text,html)
        self.assertIn("/api/operations-manager/settings",js)
        self.assertIn("/api/operations-manager/job",js)
        self.assertIn("automated_paper_submission_enabled:false",js)
        self.assertIn("paper_only:true",js)
        self.assertIn("live_submission_enabled:false",js)

if __name__=="__main__":
    unittest.main()
