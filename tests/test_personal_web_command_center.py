import unittest
from pathlib import Path

class TestCommandCenterUI(unittest.TestCase):
    def test_contract(self):
        root=Path(__file__).resolve().parents[1]
        html=(root/"web_controller/static/index.html").read_text(encoding="utf-8")
        js=(root/"web_controller/static/app.js").read_text(encoding="utf-8")
        self.assertIn("Today's Command Center",html)
        self.assertIn("Validation / 검증",html)
        self.assertIn("Safety / 안전",html)
        self.assertIn("loadCommandCenter",js)
        self.assertIn("/api/qualification",js)
        self.assertIn("/api/operations-manager",js)
        self.assertIn("actual_live_orders_submitted",js)
        self.assertIn("Emergency Stop",html)

if __name__=="__main__":
    unittest.main()
