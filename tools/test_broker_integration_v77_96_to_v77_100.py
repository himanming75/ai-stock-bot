import tempfile,unittest
from pathlib import Path
from broker_integration.broker_integration_pipeline_v77_96_100 import *

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
        self.cert=self.r/"cert.json";self.cfg=self.r/"cfg.json"
        write_json(self.cert,{"stage":"V77.95","status":"PASS",
          "certification_scope":"BROKER_INTEGRATION_SKELETON_ELIGIBILITY_ONLY",
          "broker_connection_approved":False,"actual_order_submission_allowed":False,
          "champion_candidate":{"candidate_id":"abc","parameters":{"fast_window":20,"slow_window":50}}})
        write_json(self.cfg,{"broker_skeleton":{"adapter_name":"OfflineBrokerAdapter",
          "mode":"offline_simulation","network_policy":"default_deny",
          "credential_policy":"no_real_credentials","order_submission_policy":"simulated_orders_only"}})
    def tearDown(self):self.t.cleanup()
    def chain(self):
        o96=self.r/"o96";a=build_broker_integration_skeleton(self.cert,self.cfg,o96)
        o97=self.r/"o97";b=build_broker_interface_contract(o96/"broker_integration_skeleton_v77_96.json",o97)
        o98=self.r/"o98";c=run_offline_broker_adapter_harness(o97/"broker_interface_contract_v77_97.json",o98)
        o99=self.r/"o99";d=run_broker_integration_safety_gate(
          o96/"broker_integration_skeleton_v77_96.json",
          o97/"broker_interface_contract_v77_97.json",
          o98/"offline_broker_adapter_harness_v77_98.json",o99)
        o100=self.r/"o100";e=issue_broker_integration_certificate(
          o96/"broker_integration_skeleton_verification_v77_96.json",
          o97/"broker_interface_contract_verification_v77_97.json",
          o98/"offline_broker_adapter_harness_verification_v77_98.json",
          o99/"broker_integration_safety_gate_verification_v77_99.json",
          o96/"broker_integration_skeleton_v77_96.json",o100)
        return a,b,c,d,e
    def test_full_chain(self):self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))
    def test_protocol_compliance(self):self.assertIsInstance(OfflineBrokerAdapter(),BrokerInterface)
    def test_buy_sell_accounting(self):
        a=OfflineBrokerAdapter(1000);o=a.submit_order("AAPL","buy",5);a.simulate_fill(o.order_id,100)
        s=a.submit_order("AAPL","sell",2);a.simulate_fill(s.order_id,120)
        self.assertEqual(a.get_account().cash,740.0);self.assertEqual(a.list_positions()[0].quantity,3)
    def test_short_sell_blocked(self):
        with self.assertRaises(ValueError):OfflineBrokerAdapter().submit_order("AAPL","sell",1)
    def test_filled_order_cancel_blocked(self):
        a=OfflineBrokerAdapter();o=a.submit_order("AAPL","buy",1);a.simulate_fill(o.order_id,10)
        with self.assertRaises(ValueError):a.cancel_order(o.order_id)
    def test_harness_expected_state(self):
        h=self.chain()[2];self.assertEqual(h["account"]["cash"],99440.0);self.assertEqual(len(h["fills"]),2)
    def test_certificate_scope(self):
        c=self.chain()[4];self.assertEqual(c["certification_scope"],"OFFLINE_BROKER_ADAPTER_DEVELOPMENT_ONLY")
        self.assertFalse(c["real_broker_connection_approved"])
        self.assertFalse(c["actual_order_submission_approved"])
    def test_safety_invariants(self):
        for x in self.chain():
            self.assertEqual(x["actual_orders_submitted"],0)
            self.assertFalse(x["network_allowed"]);self.assertFalse(x["broker_connected"])
    def test_invalid_certificate_rejected(self):
        write_json(self.cert,{"stage":"V77.95","status":"FAIL"})
        self.assertEqual(build_broker_integration_skeleton(self.cert,self.cfg,self.r/"bad")["status"],"FAIL")
    def test_invalid_order_rejected(self):
        a=OfflineBrokerAdapter()
        with self.assertRaises(ValueError):a.submit_order("", "buy", 1)
        with self.assertRaises(ValueError):a.submit_order("AAPL", "hold", 1)
        with self.assertRaises(ValueError):a.submit_order("AAPL", "buy", 0)
    def test_health_has_no_credentials(self):
        h=OfflineBrokerAdapter().health()
        self.assertFalse(h["real_credentials_loaded"]);self.assertFalse(h["live_order_submission_enabled"])
    def test_deterministic_digest(self):
        self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))
if __name__=="__main__":unittest.main()
