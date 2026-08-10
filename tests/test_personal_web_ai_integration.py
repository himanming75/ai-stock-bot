import tempfile, unittest
from pathlib import Path
from web_controller.state import build_dashboard

class TestPersonalWebAIIntegration(unittest.TestCase):
    def test_ai_section_present_and_safe(self):
        with tempfile.TemporaryDirectory() as t:
            d=build_dashboard(Path(t))
            self.assertIn("ai",d)
            self.assertFalse(d["ai"]["automatic_execution_change"])
            self.assertFalse(d["ai"]["automatic_model_promotion"])
            self.assertFalse(d["ai"]["live_trading"])
            self.assertTrue(d["safety"]["local_bind_only"])
            self.assertEqual(d["safety"]["actual_live_orders_submitted"],0)

if __name__=="__main__":
    unittest.main()
