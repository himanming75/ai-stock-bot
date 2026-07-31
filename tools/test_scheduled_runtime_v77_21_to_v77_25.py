from __future__ import annotations
import tempfile,unittest,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from broker.scheduled_runtime_pipeline_v77_21_25 import *
class Tests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
  self.cert=self.r/"v77_20.json"
  write_json(self.cert,{"certificate_id":"PAPER-RUNTIME-AUDIT-V77.20","status":"PASS","certificate_sha256":"abc"})
 def tearDown(self):self.t.cleanup()
 def chain(self):
  o21=self.r/"o21";s21=build_scheduler(self.cert,o21,interval_seconds=10,run_count=4)
  schedule=o21/"paper_runtime_scheduler_v77_21.json"
  o22=self.r/"o22";s22=build_execution_ledger(schedule,o22)
  ledger=o22/"scheduled_session_execution_ledger_v77_22.json"
  o23=self.r/"o23";s23=run_watchdog(ledger,o23)
  watchdog=o23/"runtime_health_watchdog_v77_23.json"
  o24=self.r/"o24";s24=auto_recover(watchdog,ledger,o24)
  o25=self.r/"o25";s25=issue_scheduled_runtime_certificate(
   o21/"paper_runtime_scheduler_verification_v77_21.json",
   o22/"scheduled_session_execution_ledger_verification_v77_22.json",
   o23/"runtime_health_watchdog_verification_v77_23.json",
   o24/"runtime_failure_auto_recovery_verification_v77_24.json",o25)
  return s21,s22,s23,s24,s25
 def test_full_chain(self):self.assertTrue(all(x.status=="PASS" for x in self.chain()))
 def test_invalid_certificate(self):
  write_json(self.cert,{"certificate_id":"BAD","status":"PASS"})
  with self.assertRaises(ScheduledRuntimeError):build_scheduler(self.cert,self.r/"x")
 def test_invalid_schedule(self):
  with self.assertRaises(ScheduledRuntimeError):build_scheduler(self.cert,self.r/"x",run_count=0)
 def test_watchdog_detects_order(self):
  o21=self.r/"o21";build_scheduler(self.cert,o21,run_count=2)
  schedule=o21/"paper_runtime_scheduler_v77_21.json";o22=self.r/"o22";build_execution_ledger(schedule,o22)
  ledger_path=o22/"scheduled_session_execution_ledger_v77_22.json";ledger=load_json(ledger_path)
  ledger["entries"][0]["orders_submitted"]=1;write_json(ledger_path,ledger)
  self.assertEqual(run_watchdog(ledger_path,self.r/"o23").status,"FAIL")
 def test_digest_deterministic(self):self.assertEqual(digest_json({"b":2,"a":1}),digest_json({"a":1,"b":2}))
if __name__=="__main__":unittest.main()
