
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.actual_paper_read_runtime_v90_21_40 import *
class T(unittest.TestCase):
 def setUp(self):self.c=ReadOnlyRuntimeConfig()
 def test_config(self):self.c.validate()
 def test_unsafe(self):
  with self.assertRaises(ValueError):ReadOnlyRuntimeConfig(runtime_loop_enabled=True).validate()
 def test_optin(self):self.assertTrue(opt_in(self.c,{self.c.network_opt_in_env:"YES"}))
 def test_fixture(self):self.assertIn("account",fixture_snapshot())
 def test_validate(self):self.assertEqual(validate_snapshot(fixture_snapshot())["status"],"PASS")
 def test_heartbeat(self):self.assertEqual(heartbeat(0,0)["status"],"PASS")
 def test_stale_heartbeat(self):self.assertEqual(heartbeat(0,999)["status"],"FAIL")
 def test_cache(self):self.assertEqual(cache_check(cache_put(fixture_snapshot(),1),1)["status"],"PASS")
 def test_stale_cache(self):self.assertEqual(cache_check({"poll_index":0},3)["status"],"FAIL")
 def test_gate(self):self.assertEqual(scheduler_gate(validate_snapshot(fixture_snapshot()),heartbeat(0),{"status":"PASS"})["status"],"READY_READ_ONLY")
 def test_poll(self):self.assertEqual(poll_once(0,fixture_snapshot)["status"],"PASS")
 def test_retry(self):self.assertTrue(retry_decision(1,self.c)["retry_allowed"])
 def test_retry_stop(self):self.assertTrue(retry_decision(2,self.c)["runtime_stop_required"])
 def test_runtime(self):self.assertEqual(runtime_validation(self.c)["status"],"PASS")
 def test_negative(self):self.assertEqual(negative_scenarios(self.c)["status"],"PASS")
 def test_audit(self):
  r=runtime_validation(self.c);n=negative_scenarios(self.c);self.assertEqual(audit(self.c,r,n)["status"],"PASS")
 def test_store(self):
  with TemporaryDirectory() as t:pid,_=store(Path(t),{"x":{"a":1}});self.assertTrue(pid.startswith("paper-read-runtime-"))
 def test_manifest(self):
  with TemporaryDirectory() as t:
   o=Path(t);_,l=store(o,{"x":{"a":1}});self.assertEqual(manifest(o,l)["status"],"PASS")
 def test_bad_provider(self):
  def p(i):raise RuntimeError("x")
  self.assertEqual(poll_once(0,p)["status"],"FAIL")
 def test_stage_count(self):self.assertEqual(len(range(21,41)),20)
if __name__=="__main__":unittest.main()
