import unittest
from pathlib import Path
from web_controller.validation_lab_api import get_payload

class TestValidationLab(unittest.TestCase):
    def test_safety_contract(self):
        d=get_payload(Path(r"C:\stock-bot"))
        self.assertIn("collector",d)
        self.assertIn("ml",d)
        self.assertIn("paper",d)
        self.assertIn("blockers",d)
        s=d["safety"]
        self.assertFalse(s["etrade_used"])
        self.assertFalse(s["broker_network_used_by_validation_lab"])
        self.assertFalse(s["paper_engine_started_by_validation_lab"])
        self.assertEqual(s["paper_orders_submitted_by_validation_lab"],0)
        self.assertEqual(s["live_orders_submitted_by_validation_lab"],0)
        self.assertFalse(s["automatic_strategy_change"])
        self.assertFalse(s["automatic_threshold_change"])
        self.assertFalse(s["automatic_model_promotion"])
        self.assertFalse(s["live_trading_enabled"])

if __name__=="__main__":
    unittest.main()
