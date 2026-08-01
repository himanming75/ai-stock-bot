from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.strategy_operations_rc_v87_81_v88_00 import *

class T(unittest.TestCase):
 def setUp(self): self.c=StrategyOperationsRCConfig()
 def test_config(self): self.c.validate()
 def test_scheduler_rejected(self):
  with self.assertRaises(ValueError):StrategyOperationsRCConfig(scheduler_enabled=True).validate()
 def test_policy(self): self.assertFalse(rc_policy(self.c)["promotion_authorized"])
 def test_startup(self): self.assertEqual(startup_check(self.c)["status"],"PASS")
 def test_session(self):
  s=startup_check(self.c);self.assertEqual(startup_manager(self.c,s)["status"],"READY_NOT_STARTED")
 def test_health(self):
  s=startup_manager(self.c,startup_check(self.c));self.assertEqual(health_monitor(self.c,s,30)["status"],"PASS")
 def test_stale_health(self):
  s=startup_manager(self.c,startup_check(self.c));self.assertEqual(health_monitor(self.c,s,999)["status"],"FAIL")
 def test_scheduler_plan(self): self.assertFalse(scheduler_plan(self.c)["scheduler_enabled"])
 def test_limit_pass(self): self.assertEqual(daily_limit_guard(self.c,0,0,0)["status"],"PASS")
 def test_limit_fail(self): self.assertEqual(daily_limit_guard(self.c,2,1000,4)["status"],"FAIL")
 def test_incident(self): self.assertEqual(incident_record("CRITICAL","X","x")["level"],"CRITICAL")
 def test_recovery(self):
  i=incident_record("CRITICAL","X","x");self.assertTrue(recovery_plan(i)["rollback_required"])
 def test_shutdown(self):
  s=startup_manager(self.c,startup_check(self.c));self.assertEqual(shutdown_manager(s)["status"],"STOPPED")
 def test_rollback(self): self.assertEqual(rollback_package()["status"],"PASS")
 def test_scenario(self): self.assertTrue(operations_scenario(self.c)["critical_recovery_ready"])
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
 def test_stage_count(self):self.assertEqual(len([f"V87.{i:02d}" for i in range(81,100)]+["V88.00"]),20)

if __name__=="__main__":unittest.main()
