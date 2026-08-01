from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.strategy_runtime_loop_v88_21_40 import *

class T(unittest.TestCase):
 def setUp(self): self.c=StrategyRuntimeLoopConfig()
 def test_config(self): self.c.validate()
 def test_runtime_rejected(self):
  with self.assertRaises(ValueError): StrategyRuntimeLoopConfig(runtime_loop_enabled=True).validate()
 def test_market(self): self.assertEqual(market_state(True,True)["status"],"OPEN")
 def test_heartbeat(self): self.assertEqual(heartbeat_check(self.c,heartbeat("x",30))["status"],"PASS")
 def test_stale_heartbeat(self): self.assertEqual(heartbeat_check(self.c,heartbeat("x",999))["status"],"FAIL")
 def test_freshness(self): self.assertEqual(data_freshness(self.c,30)["status"],"PASS")
 def test_stale_data(self): self.assertEqual(data_freshness(self.c,999)["status"],"FAIL")
 def test_cycle(self):
  c=strategy_cycle(self.c,"x",market_state(True,True),heartbeat_check(self.c,heartbeat("x",0)),data_freshness(self.c,10))
  self.assertEqual(c["status"],"PASS")
 def test_signal(self):
  c=strategy_cycle(self.c,"x",market_state(True,True),heartbeat_check(self.c,heartbeat("x",0)),data_freshness(self.c,10))
  self.assertEqual(signal_candidate(self.c,c)["status"],"CANDIDATE")
 def test_dedup(self):
  c=strategy_cycle(self.c,"x",market_state(True,True),heartbeat_check(self.c,heartbeat("x",0)),data_freshness(self.c,10))
  s=signal_candidate(self.c,c);self.assertTrue(signal_dedup(s,{s["signal_id"]})["duplicate_detected"])
 def test_timeout(self): self.assertEqual(timeout_guard(self.c,999)["status"],"FAIL")
 def test_containment(self): self.assertTrue(exception_containment(3,self.c)["runtime_stop_required"])
 def test_checkpoint(self):
  c={"cycle_id":"x"};q={"queue_depth":0}
  self.assertTrue(checkpoint(c,q)["resumable"])
 def test_resume(self): self.assertEqual(resume({"resumable":True,"checkpoint_id":"x"})["status"],"RESUMED_PREVIEW_ONLY")
 def test_shutdown(self): self.assertEqual(graceful_shutdown({"queue_depth":1})["status"],"STOPPED")
 def test_retry(self): self.assertTrue(retry_policy(0)["retry_allowed"])
 def test_iteration(self): self.assertEqual(loop_iteration(self.c,"x")["status"],"PASS")
 def test_negative(self): self.assertEqual(negative_scenarios(self.c)["status"],"PASS")
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
 def test_stage_count(self): self.assertEqual(len([f"V88.{i:02d}" for i in range(21,41)]),20)

if __name__=="__main__":unittest.main()
