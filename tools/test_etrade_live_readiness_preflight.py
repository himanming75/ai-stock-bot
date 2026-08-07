from pathlib import Path
import tempfile, unittest, os
from tools.etrade_live_readiness_preflight import build

class Tests(unittest.TestCase):
    def test_read_only_contract(self):
        with tempfile.TemporaryDirectory() as td:
            r=build(Path(td))
            c=r["contracts"]
            self.assertFalse(c["broker_write_performed"])
            self.assertFalse(c["live_order_submitted"])
            self.assertFalse(c["trading_configuration_changed"])
            self.assertFalse(c["live_auto_enable"])

    def test_stage1_policy_small(self):
        with tempfile.TemporaryDirectory() as td:
            r=build(Path(td))
            p=r["stage1_policy"]
            self.assertEqual(p["max_live_order_notional"],25.0)
            self.assertEqual(p["max_live_orders_per_day"],1)
            self.assertTrue(p["manual_arm_required"])

    def test_no_secret_values(self):
        os.environ["ETRADE_CONSUMER_KEY"]="SECRET_SHOULD_NOT_APPEAR"
        try:
            with tempfile.TemporaryDirectory() as td:
                r=build(Path(td))
                self.assertNotIn("SECRET_SHOULD_NOT_APPEAR",str(r))
        finally:
            os.environ.pop("ETRADE_CONSUMER_KEY",None)

if __name__=="__main__":
    unittest.main()
