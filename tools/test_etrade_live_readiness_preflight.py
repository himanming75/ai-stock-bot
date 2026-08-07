from pathlib import Path
import tempfile, unittest, os
from tools.etrade_live_readiness_preflight import build, CANONICAL_STACK

class Tests(unittest.TestCase):
    def test_contract_no_live_write(self):
        with tempfile.TemporaryDirectory() as td:
            r=build(Path(td),False)
            c=r["contracts"]
            self.assertFalse(c["broker_write_performed"])
            self.assertFalse(c["live_order_submitted"])
            self.assertFalse(c["live_auto_enable"])
            self.assertFalse(c["existing_etrade_adapter_modified"])

    def test_manual_arm_and_kill_switch(self):
        with tempfile.TemporaryDirectory() as td:
            p=build(Path(td),False)["stage1_policy"]
            self.assertTrue(p["manual_arm_required"])
            self.assertTrue(p["kill_switch_required"])
            self.assertEqual(p["max_live_orders_per_day"],1)
            self.assertEqual(p["max_live_order_notional"],25.0)

    def test_secret_values_not_exposed(self):
        os.environ["ETRADE_CONSUMER_KEY"]="DO_NOT_EXPOSE"
        try:
            with tempfile.TemporaryDirectory() as td:
                r=build(Path(td),False)
                self.assertNotIn("DO_NOT_EXPOSE",str(r))
        finally:
            os.environ.pop("ETRADE_CONSUMER_KEY",None)

    def test_canonical_roles_exist_contract(self):
        self.assertIn("adapter_foundation",CANONICAL_STACK)
        self.assertIn("oauth_session",CANONICAL_STACK)
        self.assertIn("production_routing",CANONICAL_STACK)
        self.assertIn("reconciliation",CANONICAL_STACK)
        self.assertIn("kill_switch",CANONICAL_STACK)

if __name__=="__main__":
    unittest.main()
