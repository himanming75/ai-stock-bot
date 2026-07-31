import tempfile,unittest
from pathlib import Path
from paper_broker.paper_broker_pipeline_v78_1_5 import *

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
        self.cert=self.r/"cert.json";self.cfg=self.r/"cfg.json"
        write_json(self.cert,{"stage":"V77.100","status":"PASS",
          "certification_scope":"OFFLINE_BROKER_ADAPTER_DEVELOPMENT_ONLY",
          "real_broker_connection_approved":False,
          "champion_candidate":{"candidate_id":"abc"}})
        write_json(self.cfg,{"paper_broker":{"adapter_name":"DeterministicPaperBrokerAdapter",
          "mode":"offline_paper","starting_cash":100000.0,
          "supported_order_types":["market","limit"],"short_selling_enabled":False}})
    def tearDown(self):self.t.cleanup()
    def chain(self):
        o1=self.r/"o1";a=build_paper_broker_foundation(self.cert,self.cfg,o1)
        o2=self.r/"o2";b=run_paper_account_position_sync(o1/"paper_broker_foundation_v78_1.json",o2)
        o3=self.r/"o3";c=run_paper_order_routing(o1/"paper_broker_foundation_v78_1.json",o3)
        o4=self.r/"o4";d=run_paper_broker_safety_gate(
          o1/"paper_broker_foundation_v78_1.json",
          o2/"paper_account_position_sync_v78_2.json",
          o3/"paper_order_routing_v78_3.json",o4)
        o5=self.r/"o5";e=issue_paper_broker_certificate(
          o1/"paper_broker_foundation_verification_v78_1.json",
          o2/"paper_account_position_sync_verification_v78_2.json",
          o3/"paper_order_routing_verification_v78_3.json",
          o4/"paper_broker_safety_gate_verification_v78_4.json",
          o1/"paper_broker_foundation_v78_1.json",o5)
        return a,b,c,d,e
    def test_full_chain(self):self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))
    def test_registry(self):
        r=AdapterRegistry();r.register("x",DeterministicPaperBrokerAdapter)
        self.assertEqual(r.names(),["x"]);self.assertIsInstance(r.create("x"),PaperBrokerAdapter)
    def test_duplicate_registry_blocked(self):
        r=AdapterRegistry();r.register("x",DeterministicPaperBrokerAdapter)
        with self.assertRaises(ValueError):r.register("x",DeterministicPaperBrokerAdapter)
    def test_duplicate_client_order_blocked(self):
        a=DeterministicPaperBrokerAdapter()
        req=PaperOrderRequest("c1","AAPL","buy",1,"market")
        a.route_order(req)
        with self.assertRaises(ValueError):a.route_order(req)
    def test_buy_sell_routing(self):
        a=DeterministicPaperBrokerAdapter(1000)
        b=a.route_order(PaperOrderRequest("c1","AAPL","buy",5,"market"));a.simulate_fill(b.broker_order_id,100)
        s=a.route_order(PaperOrderRequest("c2","AAPL","sell",2,"market"));a.simulate_fill(s.broker_order_id,120)
        self.assertEqual(a.sync_account().cash,740.0);self.assertEqual(a.sync_positions()[0].quantity,3)
    def test_short_sell_blocked(self):
        with self.assertRaises(ValueError):
            DeterministicPaperBrokerAdapter().route_order(PaperOrderRequest("c","AAPL","sell",1,"market"))
    def test_routing_event_ids_unique(self):
        events=self.chain()[2]["events"]
        self.assertEqual(len({x["event_id"] for x in events}),len(events))
    def test_certificate_scope(self):
        c=self.chain()[4]
        self.assertEqual(c["certification_scope"],"OFFLINE_PAPER_BROKER_RUNTIME_ONLY")
        self.assertFalse(c["real_broker_connection_approved"])
    def test_safety_invariants(self):
        for x in self.chain():
            self.assertEqual(x["actual_orders_submitted"],0)
            self.assertFalse(x["network_allowed"]);self.assertFalse(x["broker_connected"])
    def test_invalid_certificate_rejected(self):
        write_json(self.cert,{"stage":"V77.100","status":"FAIL"})
        self.assertEqual(build_paper_broker_foundation(self.cert,self.cfg,self.r/"bad")["status"],"FAIL")
    def test_invalid_limit_order_rejected(self):
        with self.assertRaises(ValueError):
            DeterministicPaperBrokerAdapter().route_order(PaperOrderRequest("c","AAPL","buy",1,"limit"))
    def test_health_no_credentials(self):
        h=DeterministicPaperBrokerAdapter().health()
        self.assertFalse(h["real_credentials_loaded"]);self.assertFalse(h["live_order_submission_enabled"])
    def test_deterministic_digest(self):
        self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))
if __name__=="__main__":unittest.main()
