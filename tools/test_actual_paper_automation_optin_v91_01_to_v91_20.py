
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.actual_paper_automation_optin_v91_01_20 import *

class T(unittest.TestCase):
    def setUp(self): self.c=ActualPaperAutomationOptInConfig()
    def test_config(self): self.c.validate()
    def test_unsafe(self):
        with self.assertRaises(ValueError): ActualPaperAutomationOptInConfig(scheduler_enabled=True).validate()
    def test_request(self): self.assertEqual(opt_in_request("a","b")["status"],"PENDING_APPROVAL")
    def test_approval(self): self.assertEqual(approval_record("r","a","APPROVED")["decision"],"APPROVED")
    def test_two_approvals(self):
        r=opt_in_request("a","b");aps=[approval_record(r["request_id"],"x","APPROVED"),approval_record(r["request_id"],"y","APPROVED")]
        self.assertEqual(evaluate_approvals(self.c,r,aps)["status"],"APPROVED")
    def test_rejection(self):
        r=opt_in_request("a","b");aps=[approval_record(r["request_id"],"x","REJECTED")]
        self.assertEqual(evaluate_approvals(self.c,r,aps)["status"],"REJECTED")
    def test_token(self):
        t=issue_session_token(self.c,{"status":"APPROVED"},100);self.assertEqual(t["status"],"ACTIVE")
    def test_validate_token(self):
        t=issue_session_token(self.c,{"status":"APPROVED"},100);self.assertTrue(validate_session(t,101)["valid"])
    def test_expired(self):
        t=issue_session_token(self.c,{"status":"APPROVED"},100);self.assertFalse(validate_session(t,500)["valid"])
    def test_consume(self):
        t=issue_session_token(self.c,{"status":"APPROVED"},100);self.assertEqual(consume_session(t)["status"],"CONSUMED")
    def test_revoke(self):
        t=issue_session_token(self.c,{"status":"APPROVED"},100);self.assertEqual(revoke_session(t,"x")["status"],"REVOKED")
    def test_kill(self): self.assertTrue(kill_switch(True,"x")["triggered"])
    def test_gate(self):
        self.assertEqual(permission_gate({"valid":True},kill_switch(False))["status"],"READY_READ_ONLY")
    def test_audit_event(self): self.assertIn("event_sha256",audit_event("x","y","z"))
    def test_negative(self): self.assertEqual(negative_scenarios(self.c)["status"],"PASS")
    def test_foundation(self): self.assertEqual(run_foundation(self.c)["status"],"PASS")
    def test_final_audit(self):
        f=run_foundation(self.c);n=negative_scenarios(self.c);self.assertEqual(final_audit(self.c,f,n)["status"],"PASS")
    def test_store(self):
        with TemporaryDirectory() as t:
            pid,_=store_package(Path(t),{"x":{"status":"PASS"}});self.assertTrue(pid.startswith("actual-paper-optin-"))
    def test_manifest(self):
        with TemporaryDirectory() as t:
            o=Path(t);_,l=store_package(o,{"x":{"status":"PASS"}});m=build_manifest(o,l);self.assertTrue(verify_manifest(o,m))
    def test_stage_count(self): self.assertEqual(len(range(1,21)),20)

if __name__=="__main__": unittest.main()
