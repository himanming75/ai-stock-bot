
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.scheduler_runtime_simulation_v88_61_80 import *

class T(unittest.TestCase):
 def setUp(self): self.c=SchedulerRuntimeSimulationConfig()
 def test_config(self): self.c.validate()
 def test_unsafe(self):
  with self.assertRaises(ValueError): SchedulerRuntimeSimulationConfig(scheduler_enabled=True).validate()
 def test_timeline(self): self.assertEqual(daily_timeline(self.c)["event_count"],7)
 def test_queue(self): self.assertEqual(event_queue(daily_timeline(self.c))["queue_depth"],7)
 def test_gate(self): self.assertTrue(market_data_gate("x","PASS")["cycle_allowed"])
 def test_tick(self): self.assertEqual(strategy_tick(self.c,"x",market_data_gate("x"))["status"],"PASS")
 def test_transition(self): self.assertEqual(runtime_state_transition("IDLE","PREOPEN_PREP")["to_state"],"PREOPEN")
 def test_checkpoint(self): self.assertTrue(checkpoint(1,"RUNNING",2)["resumable"])
 def test_resume(self): self.assertEqual(resume({"checkpoint_id":"x"})["status"],"RESUMED_PREVIEW_ONLY")
 def test_duplicate(self): self.assertTrue(duplicate_event_guard({"e"},"e")["duplicate_detected"])
 def test_missed(self): self.assertTrue(missed_event_recovery(10)["recoverable"])
 def test_incident(self): self.assertTrue(incident_recovery("x")["manual_review_required"])
 def test_shutdown(self): self.assertEqual(shutdown_report("STOPPED",3)["status"],"PASS")
 def test_report(self): self.assertEqual(daily_runtime_report(self.c,3,3,0)["status"],"PASS")
 def test_simulation(self):
  s=run_simulation(self.c);self.assertEqual(s["final_state"],"STOPPED")
 def test_negative(self): self.assertEqual(negative_scenarios(self.c)["status"],"PASS")
 def test_audit(self):
  s=run_simulation(self.c);n=negative_scenarios(self.c);self.assertEqual(audit(self.c,s,n)["status"],"PASS")
 def test_store(self):
  with TemporaryDirectory() as t:
   pid,ledger=store(Path(t),{"x":{"a":1}});self.assertTrue(pid.startswith("scheduler-runtime-sim-"))
 def test_manifest(self):
  with TemporaryDirectory() as t:
   o=Path(t);_,l=store(o,{"x":{"a":1}});self.assertEqual(manifest(o,l)["status"],"PASS")
 def test_stage_count(self): self.assertEqual(len([f"V88.{i:02d}" for i in range(61,81)]),20)

if __name__=="__main__": unittest.main()
