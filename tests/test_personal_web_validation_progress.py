import unittest
from pathlib import Path
from web_controller.validation_lab_api import get_payload

class TestValidationProgressTracker(unittest.TestCase):
    def test_progress_contract(self):
        d=get_payload(Path(r"C:\stock-bot"))
        p=d["progress"]
        self.assertEqual(p["trading_days_target"],10)
        self.assertEqual(p["resolved_outcomes_target"],200)
        self.assertGreaterEqual(p["trading_days_completed"],0)
        self.assertLessEqual(p["trading_days_completed"],10)
        self.assertGreaterEqual(p["resolved_outcomes"],0)
        self.assertFalse(p["synthetic_progress_used"])
        self.assertFalse(p["future_outcomes_fabricated"])
        self.assertIn("gates",p)
        self.assertIn("next_milestone",p)

if __name__=="__main__":
    unittest.main()
