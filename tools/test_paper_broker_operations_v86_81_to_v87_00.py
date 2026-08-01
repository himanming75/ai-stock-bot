from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.paper_broker_operations_v86_81_v87_00 import *

class T(unittest.TestCase):
 def setUp(self): self.c=PaperBrokerOperationsConfig()
 def test_config(self): self.c.validate()
 def test_auto_order_rejected(self):
  with self.assertRaises(ValueError):PaperBrokerOperationsConfig(auto_order_enabled=True).validate()
 def test_policy(self): self.assertFalse(release_policy(self.c)["promotion_authorized"])
 def test_profile(self): self.assertEqual(operations_profile(self.c)["daily_order_limit"],1)
 def test_start_request(self): self.assertEqual(start_request("u","r")["status"],"PENDING")
 def test_start_gate(self):
  r=start_request("u","r");self.assertEqual(start_gate(self.c,r)["status"],"PASS")
 def test_session(self):
  r=start_request("u","r");g=start_gate(self.c,r);self.assertEqual(issue_session(self.c,r,g)["status"],"READY_NOT_STARTED")
 def test_health(self):
  r=start_request("u","r");g=start_gate(self.c,r);s=issue_session(self.c,r,g)
  self.assertEqual(health_check(s)["status"],"PASS")
 def test_limits_pass(self): self.assertEqual(daily_limit_guard(self.c,1,100,1)["status"],"PASS")
 def test_limits_fail(self): self.assertEqual(daily_limit_guard(self.c,2,1000,4)["status"],"FAIL")
 def test_stop(self):
  r=start_request("u","r");g=start_gate(self.c,r);s=issue_session(self.c,r,g)
  self.assertEqual(stop_session(s,stop_request("u","x"))["status"],"STOPPED")
 def test_incident(self): self.assertEqual(incident_record("CRITICAL","X","x")["severity"],"CRITICAL")
 def test_rollback(self): self.assertEqual(rollback_plan()["status"],"PASS")
 def test_runbook(self): self.assertFalse(runbook()["contains_order_submission_step"])
 def test_checklist(self): self.assertEqual(deployment_checklist(self.c)["status"],"PASS")
 def test_scenario(self): self.assertTrue(operations_scenario(self.c)["session_stopped"])
 def test_store_reuse(self):
  with TemporaryDirectory() as t:
   o=Path(t);store(o,{"a":{"x":1}});self.assertTrue(store(o,{"a":{"x":1}})["reused"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   o=Path(t);z=store(o,{"a":{"x":1}});m=manifest(o,z["ledger"]);self.assertTrue(verify_manifest(o,m))
 def test_bad_source(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c";p.write_text("{}")
   with self.assertRaises(ValueError):validate_source(p)
 def test_stage_count(self): self.assertEqual(len([f"V86.{i:02d}" for i in range(81,100)]+["V87.00"]),20)

if __name__=="__main__":unittest.main()
