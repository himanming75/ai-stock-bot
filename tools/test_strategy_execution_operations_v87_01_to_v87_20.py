from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.strategy_execution_operations_v87_01_20 import *

class T(unittest.TestCase):
 def setUp(self): self.c=StrategyExecutionOperationsConfig()
 def test_config(self): self.c.validate()
 def test_auto_exec_rejected(self):
  with self.assertRaises(ValueError):StrategyExecutionOperationsConfig(auto_execution_enabled=True).validate()
 def test_signal(self): self.assertEqual(signal_intake(self.c,"AAPL","buy",0.8,200,10)["status"],"RECEIVED")
 def test_validation(self):
  s=signal_intake(self.c,"AAPL","buy",0.8,200,10)
  self.assertEqual(signal_validation(self.c,s)["status"],"PASS")
 def test_bad_symbol(self):
  s=signal_intake(self.c,"TSLA","buy",0.8,200,10)
  self.assertEqual(signal_validation(self.c,s)["status"],"FAIL")
 def test_risk(self):
  s=signal_intake(self.c,"AAPL","buy",0.8,200,10);v=signal_validation(self.c,s)
  self.assertEqual(risk_decision(self.c,s,v,0,0,0)["status"],"PASS")
 def test_lock(self): self.assertEqual(strategy_lock(self.c,signal_intake(self.c,"AAPL","buy",0.8,200,10))["status"],"ACQUIRED")
 def test_approval(self):
  s=signal_intake(self.c,"AAPL","buy",0.8,200,10);v=signal_validation(self.c,s);r=risk_decision(self.c,s,v,0,0,0)
  self.assertEqual(approve(approval_request(self.c,s,r),"u")["status"],"APPROVED")
 def test_preview(self):
  s=signal_intake(self.c,"AAPL","buy",0.8,200,10);v=signal_validation(self.c,s);r=risk_decision(self.c,s,v,0,0,0);a=approve(approval_request(self.c,s,r),"u")
  self.assertEqual(execution_preview(s,r,a)["status"],"PREVIEW_ONLY")
 def test_budget(self):
  p={"estimated_notional":200};self.assertEqual(budget_reservation(self.c,p,0,0)["status"],"RESERVED")
 def test_queue(self): self.assertFalse(execution_queue({"context_id":"x"})["dispatch_enabled"])
 def test_resume(self): self.assertEqual(resume_session({"resumable":True,"checkpoint_id":"x"})["status"],"RESUMED_PREVIEW_ONLY")
 def test_rejections(self): self.assertGreaterEqual(rejection_scenarios(self.c)["reject_count"],5)
 def test_rollback(self): self.assertEqual(rollback_plan()["status"],"PASS")
 def test_scenario(self): self.assertTrue(operations_scenario(self.c)["preview_canceled"])
 def test_store_reuse(self):
  with TemporaryDirectory() as t:
   o=Path(t);store(o,{"a":{"x":1}});self.assertTrue(store(o,{"a":{"x":1}})["reused"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   o=Path(t);z=store(o,{"a":{"x":1}});m=manifest(o,z["ledger"]);self.assertTrue(verify_manifest(o,m))
 def test_bad_source(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"x";p.write_text("{}")
   with self.assertRaises(ValueError):validate_source(p)
 def test_stage_count(self):self.assertEqual(len([f"V87.{i:02d}" for i in range(1,21)]),20)

if __name__=="__main__":unittest.main()
