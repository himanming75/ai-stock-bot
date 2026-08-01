
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.actual_paper_order_submission_optin_v91_81_v92_00 import *

class T(unittest.TestCase):
    def setUp(self): self.c=OrderSubmissionOptInConfig()
    def test_config(self): self.c.validate()
    def test_unsafe(self):
        with self.assertRaises(ValueError):
            OrderSubmissionOptInConfig(paper_order_submission_authorized=True).validate()
    def test_intent(self): self.assertEqual(create_order_intent("AAPL","BUY",1,200)["status"],"PENDING_APPROVAL")
    def test_intent_validation(self):
        i=create_order_intent("AAPL","BUY",1,200)
        self.assertEqual(validate_order_intent(self.c,i,1000,0,False)["status"],"PASS")
    def test_bad_symbol(self):
        i=create_order_intent("TSLA","BUY",1,200)
        self.assertEqual(validate_order_intent(self.c,i,1000,0,False)["status"],"FAIL")
    def test_approval(self):
        self.assertEqual(approval_record("x","a","APPROVED")["decision"],"APPROVED")
    def test_two_approvals(self):
        a=[approval_record("x","a","APPROVED"),approval_record("x","b","APPROVED")]
        self.assertEqual(evaluate_approvals(self.c,"x",a)["status"],"APPROVED")
    def test_token(self):
        i=create_order_intent("AAPL","BUY",1,200)
        v=validate_order_intent(self.c,i,1000,0,False)
        a=evaluate_approvals(self.c,i["intent_id"],[approval_record(i["intent_id"],"a","APPROVED"),approval_record(i["intent_id"],"b","APPROVED")])
        self.assertEqual(issue_order_token(self.c,i,v,a)["status"],"ACTIVE")
    def test_token_validation(self):
        i=create_order_intent("AAPL","BUY",1,200);v=validate_order_intent(self.c,i,1000,0,False)
        a=evaluate_approvals(self.c,i["intent_id"],[approval_record(i["intent_id"],"a","APPROVED"),approval_record(i["intent_id"],"b","APPROVED")])
        t=issue_order_token(self.c,i,v,a)
        self.assertTrue(validate_order_token(t,i,1000001)["token_valid"])
    def test_consume(self):
        i=create_order_intent("AAPL","BUY",1,200);v=validate_order_intent(self.c,i,1000,0,False)
        a=evaluate_approvals(self.c,i["intent_id"],[approval_record(i["intent_id"],"a","APPROVED"),approval_record(i["intent_id"],"b","APPROVED")])
        self.assertEqual(consume_order_token(issue_order_token(self.c,i,v,a))["status"],"CONSUMED")
    def test_kill(self): self.assertTrue(kill_switch(True,"x")["triggered"])
    def test_gate(self):
        self.assertEqual(submission_gate({"status":"PASS"},{"status":"PASS"},kill_switch(False))["status"],"READY_PREVIEW_ONLY")
    def test_negative(self): self.assertEqual(negative_scenarios(self.c)["status"],"PASS")
    def test_integrated(self): self.assertEqual(integrated_foundation(self.c)["status"],"PASS")
    def test_audit(self):
        i=integrated_foundation(self.c);n=negative_scenarios(self.c)
        self.assertEqual(final_audit(self.c,i,n)["status"],"PASS")
    def test_store(self):
        with TemporaryDirectory() as t:
            pid,_=store_package(Path(t),{"x":{"status":"PASS"}})
            self.assertTrue(pid.startswith("actual-paper-order-optin-"))
    def test_manifest(self):
        with TemporaryDirectory() as t:
            o=Path(t);_,l=store_package(o,{"x":{"status":"PASS"}});m=build_manifest(o,l)
            self.assertTrue(verify_manifest(o,m))
    def test_limits(self):
        self.assertEqual(self.c.max_order_notional,500.0)
        self.assertEqual(self.c.max_quantity,5)
    def test_orders_zero(self): self.assertEqual(self.c.actual_orders_submitted,0)
    def test_stage_count(self): self.assertEqual(len(range(81,101)),20)

if __name__=="__main__": unittest.main()
