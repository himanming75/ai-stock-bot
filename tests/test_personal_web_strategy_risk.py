import unittest
from pathlib import Path

class TestPersonalWebStrategyRisk(unittest.TestCase):
    def test_ui_contract(self):
        root=Path(__file__).resolve().parents[1]
        html=(root/"web_controller/static/index.html").read_text(encoding="utf-8")
        js=(root/"web_controller/static/app.js").read_text(encoding="utf-8")
        self.assertIn("Save Paper Settings",html)
        self.assertIn("AI Recommendation (Read Only)",html)
        self.assertIn("riskOrderNotional",html)
        self.assertIn("/api/strategy-config/save",js)
        self.assertIn("/api/strategy-config/validate",js)
        self.assertIn("paper_only:true",js)
        self.assertIn("live_submission_enabled:false",js)
        self.assertNotIn("automatic strategy change",html.lower())

if __name__=="__main__":
    unittest.main()
