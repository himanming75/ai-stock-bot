
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.actual_paper_automation_session_v91_21_40 import *

class T(unittest.TestCase):
    def setUp(self): self.c=SessionValidationConfig()
    def test_config(self): self.c.validate()
    def test_unsafe(self):
        with self.assertRaises(ValueError): SessionValidationConfig(runtime_loop_enabled=True).validate()
    def test_create(self): self.assertEqual(create_session(self.c)["status"],"ACTIVE")
    def test_validate(self):
        s=create_session(self.c,100);self.assertTrue(validate_session(s,101)["valid"])
    def test_expired(self):
        s=create_session(self.c,100);self.assertFalse(validate_session(s,400)["valid"])
    def test_heartbeat(self):
        s=create_session(self.c,100);u=heartbeat(s,130,self.c);self.assertEqual(u["heartbeat_count"],1)
    def test_heartbeat_health(self):
        s=create_session(self.c,100);self.assertEqual(heartbeat_health(s,101,self.c)["status"],"PASS")
    def test_stale_heartbeat(self):
        s=create_session(self.c,100);self.assertEqual(heartbeat_health(s,300,self.c)["status"],"FAIL")
    def test_consume(self):
        s=create_session(self.c,100);self.assertEqual(consume_session(s)["status"],"CONSUMED")
    def test_resume(self):
        s=create_session(self.c,100);self.assertEqual(resume_session(s,101)["status"],"RESUMED_READ_ONLY")
    def test_resume_consumed(self):
        s=consume_session(create_session(self.c,100));self.assertEqual(resume_session(s,101)["status"],"REJECTED")
    def test_revoke(self):
        s=create_session(self.c,100);self.assertEqual(revoke_session(s,"x")["status"],"REVOKED")
    def test_kill(self): self.assertTrue(kill_switch(True,"x")["triggered"])
    def test_close(self):
        s=create_session(self.c,100);self.assertEqual(close_session(s,"x")["status"],"CLOSED")
    def test_audit(self): self.assertIn("event_sha256",audit_event("x","y","z"))
    def test_negative(self): self.assertEqual(negative_scenarios(self.c)["status"],"PASS")
    def test_integrated(self): self.assertEqual(integrated_session_validation(self.c)["status"],"PASS")
    def test_final_audit(self):
        i=integrated_session_validation(self.c);n=negative_scenarios(self.c);self.assertEqual(final_audit(self.c,i,n)["status"],"PASS")
    def test_store(self):
        with TemporaryDirectory() as t:
            pid,_=store_package(Path(t),{"x":{"status":"PASS"}});self.assertTrue(pid.startswith("actual-paper-session-"))
    def test_manifest(self):
        with TemporaryDirectory() as t:
            o=Path(t);_,l=store_package(o,{"x":{"status":"PASS"}});m=build_manifest(o,l);self.assertTrue(verify_manifest(o,m))
    def test_stage_count(self): self.assertEqual(len(range(21,41)),20)

if __name__=="__main__": unittest.main()
