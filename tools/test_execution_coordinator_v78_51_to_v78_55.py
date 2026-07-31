import tempfile,unittest
from pathlib import Path
from execution_coordinator.execution_coordinator_pipeline_v78_51_55 import *

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.r=Path(self.t.name)
        self.cert=self.r/"cert.json"
        self.cfg=self.r/"cfg.json"
        self.decisions=self.r/"decisions.json"
        self.normalization=self.r/"normalization.json"

        write_json(self.cert,{
            "stage":"V78.50","status":"PASS",
            "certification_scope":"OFFLINE_EXECUTION_COORDINATOR_DEVELOPMENT_ONLY",
            "champion_candidate":{"candidate_id":"abc"}
        })
        write_json(self.cfg,{
            "execution_coordinator":{
                "order_type":"market","time_in_force":"day","limit_offset_bps":5,
                "allow_paper_broker_dispatch":True,"allow_real_broker_dispatch":False
            }
        })
        write_json(self.normalization,{
            "stage":"V78.42","status":"PASS",
            "risk_requests":[
                {"risk_request_id":"r1","normalized_signal_id":"n1","candidate_id":"abc","symbol":"AAPL",
                 "timestamp":"t1","side":"buy","requested_notional":1000.0,"reference_price":100.0,
                 "current_cash":100000.0,"current_position_quantity":10,"risk_request_sha256":"x"},
                {"risk_request_id":"r2","normalized_signal_id":"n2","candidate_id":"abc","symbol":"AAPL",
                 "timestamp":"t2","side":"sell","requested_notional":1000.0,"reference_price":100.0,
                 "current_cash":100000.0,"current_position_quantity":10,"risk_request_sha256":"y"}
            ]
        })
        write_json(self.decisions,{
            "stage":"V78.43","status":"PASS",
            "risk_decisions":[
                {"risk_decision_id":"d1","risk_request_id":"r1","decision":"APPROVE",
                 "approved_notional":1000.0,"approved_quantity":10,"reason":"ok","risk_decision_sha256":"a"},
                {"risk_decision_id":"d2","risk_request_id":"r2","decision":"APPROVE",
                 "approved_notional":1000.0,"approved_quantity":10,"reason":"ok","risk_decision_sha256":"b"}
            ]
        })

    def tearDown(self):
        self.t.cleanup()

    def chain(self):
        o51=self.r/"o51"
        a=build_execution_coordinator_foundation(self.cert,self.cfg,o51)
        o52=self.r/"o52"
        b=run_approved_decision_to_order_intent(
            o51/"execution_coordinator_foundation_v78_51.json",
            self.decisions,self.normalization,o52)
        o53=self.r/"o53"
        c=run_execution_queue_idempotency(
            o52/"approved_decision_to_paper_order_intent_v78_52.json",o53)
        o54=self.r/"o54"
        d=run_execution_coordinator_safety_gate(
            o51/"execution_coordinator_foundation_v78_51.json",
            o52/"approved_decision_to_paper_order_intent_v78_52.json",
            o53/"execution_queue_idempotency_v78_53.json",o54)
        o55=self.r/"o55"
        e=issue_execution_coordinator_certificate(
            o51/"execution_coordinator_foundation_verification_v78_51.json",
            o52/"approved_decision_to_paper_order_intent_verification_v78_52.json",
            o53/"execution_queue_idempotency_verification_v78_53.json",
            o54/"execution_coordinator_safety_gate_verification_v78_54.json",
            o51/"execution_coordinator_foundation_v78_51.json",o55)
        return a,b,c,d,e

    def test_full_chain(self):
        self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))

    def test_rejected_decision_creates_no_intent(self):
        result=build_order_intent(
            {"risk_decision_id":"d","risk_request_id":"r","decision":"REJECT","approved_quantity":0},
            {"risk_request_id":"r","candidate_id":"c","symbol":"AAPL","side":"buy","reference_price":100},
            {"order_type":"market","time_in_force":"day"}
        )
        self.assertIsNone(result)

    def test_limit_price(self):
        intent=build_order_intent(
            {"risk_decision_id":"d","risk_request_id":"r","decision":"APPROVE","approved_quantity":2},
            {"risk_request_id":"r","candidate_id":"c","symbol":"AAPL","side":"buy","reference_price":100},
            {"order_type":"limit","time_in_force":"day","limit_offset_bps":10}
        )
        self.assertEqual(intent.limit_price,100.1)

    def test_duplicate_enqueue_blocked(self):
        q=ExecutionQueue()
        intent=PaperOrderIntent("i","d","r","c","AAPL","buy",1,"market","day",None,100,"h")
        q.enqueue(intent)
        with self.assertRaises(ValueError):
            q.enqueue(intent)

    def test_fifo(self):
        q=ExecutionQueue()
        a=PaperOrderIntent("a","d1","r1","c","AAPL","buy",1,"market","day",None,100,"h1")
        b=PaperOrderIntent("b","d2","r2","c","AAPL","sell",1,"market","day",None,100,"h2")
        q.enqueue(a);q.enqueue(b)
        self.assertEqual(q.dequeue().order_intent_id,"a")

    def test_cancel_dispatched_blocked(self):
        q=ExecutionQueue()
        a=PaperOrderIntent("a","d1","r1","c","AAPL","buy",1,"market","day",None,100,"h1")
        q.enqueue(a);q.dequeue()
        with self.assertRaises(ValueError):
            q.cancel("a")

    def test_certificate_scope(self):
        c=self.chain()[4]
        self.assertEqual(c["certification_scope"],"OFFLINE_PAPER_BROKER_INTEGRATION_DEVELOPMENT_ONLY")
        self.assertFalse(c["actual_order_submission_approved"])

    def test_invalid_certificate_rejected(self):
        write_json(self.cert,{"stage":"V78.50","status":"FAIL"})
        self.assertEqual(
            build_execution_coordinator_foundation(self.cert,self.cfg,self.r/"bad")["status"],
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
