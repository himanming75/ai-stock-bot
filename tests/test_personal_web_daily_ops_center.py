import unittest
from pathlib import Path
from web_controller.daily_ops_api import get_payload,action_payload

class TestDailyOpsCenter(unittest.TestCase):
    def test_safety(self):
        d=get_payload(Path(r"C:\stock-bot"))
        s=d["safety"]
        self.assertFalse(s["etrade_used"])
        self.assertFalse(s["broker_network_used_by_daily_ops"])
        self.assertFalse(s["paper_engine_started_by_daily_ops"])
        self.assertEqual(s["paper_orders_submitted_by_daily_ops"],0)
        self.assertEqual(s["live_orders_submitted_by_daily_ops"],0)
        self.assertFalse(s["automatic_strategy_change"])
        self.assertFalse(s["automatic_threshold_change"])
        self.assertFalse(s["automatic_model_promotion"])
        self.assertFalse(s["live_trading_enabled"])

    def test_daily_check_allowed(self):
        r=action_payload(Path(r"C:\stock-bot"),{"action":"run_daily_check"})
        self.assertTrue(r["ok"])
        self.assertIn("checks",r)
        self.assertEqual(r["safety"]["live_orders_submitted_by_daily_ops"],0)

if __name__=="__main__":
    unittest.main()
