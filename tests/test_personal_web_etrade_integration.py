import unittest
from pathlib import Path
from web_controller.etrade_api import get_payload,action_payload

class TestEtradeWebIntegration(unittest.TestCase):
    def test_safety(self):
        d=get_payload(Path(r"C:\stock-bot"))
        self.assertIn("stack",d)
        self.assertIn("audit",d)
        self.assertFalse(d["credentials"]["credential_values_exposed"])
        self.assertFalse(d["safety"]["production_order_post_allowed"])
        self.assertFalse(d["safety"]["live_trading_enabled"])
        self.assertFalse(d["safety"]["web_live_order_action_available"])
        self.assertEqual(d["safety"]["actual_live_orders_submitted"],0)

    def test_preflight_is_offline(self):
        r=action_payload(Path(r"C:\stock-bot"),{"action":"credential_preflight"})
        self.assertTrue(r["ok"])
        self.assertFalse(r["credential_values_exposed"])
        self.assertFalse(r["network_call_performed"])
        self.assertFalse(r["order_call_performed"])

if __name__=="__main__":
    unittest.main()
