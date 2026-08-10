import os,unittest
from pathlib import Path
from web_controller.etrade_api import get_payload,action_payload

class TestProductionReadOnlyWeb(unittest.TestCase):
    def test_unconnected_is_blocked(self):
        keys=[
            "ETRADE_ENVIRONMENT","ETRADE_ALLOW_PRODUCTION_READ",
            "ETRADE_ACCESS_TOKEN","ETRADE_ACCESS_SECRET",
        ]
        old={k:os.environ.get(k) for k in keys}
        try:
            for k in keys:
                os.environ.pop(k,None)
            r=action_payload(Path(r"C:\stock-bot"),{"action":"run_production_readonly_snapshot"})
            self.assertFalse(r["ok"])
            self.assertEqual(r["actual_live_orders_submitted"],0)
            self.assertFalse(r["live_trading_enabled"])
        finally:
            for k,v in old.items():
                if v is None: os.environ.pop(k,None)
                else: os.environ[k]=v

    def test_payload_never_exposes_credentials(self):
        d=get_payload(Path(r"C:\stock-bot"))
        self.assertFalse(d["production_session"]["credential_values_exposed"])
        self.assertFalse(d["safety"]["production_order_post_allowed"])
        self.assertFalse(d["safety"]["live_trading_enabled"])
        self.assertEqual(d["safety"]["actual_live_orders_submitted"],0)

if __name__=="__main__":
    unittest.main()
