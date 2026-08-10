import unittest
from pathlib import Path
from web_controller.backtest_api import get_payload

class TestBacktestWebIntegration(unittest.TestCase):
    def test_payload_safety(self):
        d=get_payload(Path(r"C:\stock-bot"))
        self.assertIn("automated",d)
        self.assertIn("canonical",d)
        self.assertIn("quality",d)
        s=d["safety"]
        self.assertTrue(s["existing_backtest_engine_reused"])
        self.assertFalse(s["new_backtest_engine_created"])
        self.assertFalse(s["new_strategy_created"])
        self.assertFalse(s["broker_write_enabled"])
        self.assertFalse(s["order_submission_enabled"])
        self.assertFalse(s["live_trading_enabled"])
        self.assertEqual(s["actual_orders_submitted"],0)

if __name__=="__main__":
    unittest.main()
