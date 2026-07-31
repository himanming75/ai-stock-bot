import tempfile,unittest
from pathlib import Path
from paper_broker_integration.paper_broker_integration_pipeline_v78_56_60 import *

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.r=Path(self.t.name)
        self.cert=self.r/"cert.json"
        self.cfg=self.r/"cfg.json"
        self.intents=self.r/"intents.json"

        write_json(self.cert,{
            "stage":"V78.55","status":"PASS",
            "certification_scope":"OFFLINE_PAPER_BROKER_INTEGRATION_DEVELOPMENT_ONLY",
            "champion_candidate":{"candidate_id":"abc"}
        })
        write_json(self.cfg,{
            "paper_broker_integration":{
                "commission_per_order":0.25,
                "slippage_bps":5.0,
                "max_fill_quantity":4,
                "allow_real_broker":False
            }
        })
        write_json(self.intents,{
            "stage":"V78.52","status":"PASS",
            "paper_order_intents":[
                {"order_intent_id":"i1","risk_decision_id":"d1","risk_request_id":"r1",
                 "candidate_id":"abc","symbol":"AAPL","side":"buy","quantity":10,
                 "order_type":"market","time_in_force":"day","limit_price":None,
                 "reference_price":100.0,"intent_sha256":"x"},
                {"order_intent_id":"i2","risk_decision_id":"d2","risk_request_id":"r2",
                 "candidate_id":"abc","symbol":"AAPL","side":"sell","quantity":10,
                 "order_type":"market","time_in_force":"day","limit_price":None,
                 "reference_price":100.0,"intent_sha256":"y"}
            ]
        })

    def tearDown(self):
        self.t.cleanup()

    def chain(self):
        o56=self.r/"o56"
        a=build_paper_broker_integration_foundation(self.cert,self.cfg,o56)
        o57=self.r/"o57"
        b=run_paper_order_submission_pipeline(
            o56/"paper_broker_integration_foundation_v78_56.json",
            self.intents,o57)
        o58=self.r/"o58"
        c=run_paper_fill_simulation(
            o56/"paper_broker_integration_foundation_v78_56.json",
            o57/"paper_order_submission_pipeline_v78_57.json",o58)
        o59=self.r/"o59"
        d=run_paper_broker_integration_safety_gate(
            o56/"paper_broker_integration_foundation_v78_56.json",
            o57/"paper_order_submission_pipeline_v78_57.json",
            o58/"paper_fill_simulation_engine_v78_58.json",o59)
        o60=self.r/"o60"
        e=issue_paper_broker_integration_certificate(
            o56/"paper_broker_integration_foundation_verification_v78_56.json",
            o57/"paper_order_submission_pipeline_verification_v78_57.json",
            o58/"paper_fill_simulation_engine_verification_v78_58.json",
            o59/"paper_broker_integration_safety_gate_verification_v78_59.json",
            o56/"paper_broker_integration_foundation_v78_56.json",o60)
        return a,b,c,d,e

    def test_full_chain(self):
        self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))

    def test_duplicate_submission_blocked(self):
        broker=OfflinePaperBroker(0,0,10)
        intent={"order_intent_id":"i","symbol":"AAPL","side":"buy","quantity":1,
                "order_type":"market","time_in_force":"day","limit_price":None,"reference_price":100}
        broker.submit(intent)
        with self.assertRaises(ValueError):
            broker.submit(intent)

    def test_partial_then_full_fill(self):
        broker=OfflinePaperBroker(0.25,5,4)
        order=broker.submit({"order_intent_id":"i","symbol":"AAPL","side":"buy","quantity":6,
                             "order_type":"market","time_in_force":"day","limit_price":None,"reference_price":100})
        first=broker.fill_next(order.broker_order_id)
        second=broker.fill_next(order.broker_order_id)
        self.assertEqual(first.fill_status,"PARTIALLY_FILLED")
        self.assertEqual(second.fill_status,"FILLED")

    def test_buy_slippage_direction(self):
        broker=OfflinePaperBroker(0,10,10)
        order=broker.submit({"order_intent_id":"i","symbol":"AAPL","side":"buy","quantity":1,
                             "order_type":"market","time_in_force":"day","limit_price":None,"reference_price":100})
        fill=broker.fill_next(order.broker_order_id)
        self.assertGreater(fill.fill_price,100)

    def test_sell_slippage_direction(self):
        broker=OfflinePaperBroker(0,10,10)
        order=broker.submit({"order_intent_id":"i","symbol":"AAPL","side":"sell","quantity":1,
                             "order_type":"market","time_in_force":"day","limit_price":None,"reference_price":100})
        fill=broker.fill_next(order.broker_order_id)
        self.assertLess(fill.fill_price,100)

    def test_filled_order_cancel_blocked(self):
        broker=OfflinePaperBroker(0,0,10)
        order=broker.submit({"order_intent_id":"i","symbol":"AAPL","side":"buy","quantity":1,
                             "order_type":"market","time_in_force":"day","limit_price":None,"reference_price":100})
        broker.fill_next(order.broker_order_id)
        with self.assertRaises(ValueError):
            broker.cancel(order.broker_order_id)

    def test_certificate_scope(self):
        c=self.chain()[4]
        self.assertEqual(c["certification_scope"],"OFFLINE_FILL_PORTFOLIO_BRIDGE_DEVELOPMENT_ONLY")
        self.assertFalse(c["actual_order_submission_approved"])

    def test_invalid_certificate_rejected(self):
        write_json(self.cert,{"stage":"V78.55","status":"FAIL"})
        self.assertEqual(
            build_paper_broker_integration_foundation(self.cert,self.cfg,self.r/"bad")["status"],
            "FAIL"
        )

    def test_safety_invariants(self):
        for x in self.chain():
            self.assertEqual(x["actual_orders_submitted"],0)
            self.assertFalse(x["network_allowed"])
            self.assertFalse(x["broker_connected"])

    def test_deterministic_digest(self):
        self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))

if __name__=="__main__":
    unittest.main()
