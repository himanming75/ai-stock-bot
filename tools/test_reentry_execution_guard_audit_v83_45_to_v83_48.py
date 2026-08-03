import json,tempfile,unittest
from pathlib import Path
from paper_runtime.reentry_execution_guard_audit_v83_45_48 import run_reentry_execution_guard_audit
def w(p,x): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x),encoding="utf-8")
class T(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(); self.r=Path(self.t.name)
  names=["ar","al","re","rp","rl","po","el","le","ep","rs","db","out"]
  for n in names: setattr(self,n,self.r/(n+".json"))
  w(self.po,{"paper_only":True,"automatic_execution_enabled":False,"broker_write_enabled":False,"order_submission_enabled":False,"live_trading_enabled":False,"external_network_enabled":False})
 def tearDown(self): self.t.cleanup()
 def run_stage(self,**k): return run_reentry_execution_guard_audit(approval_result_path=self.ar,approval_lock_path=self.al,reentry_plan_path=self.re,retry_plan_path=self.rp,retry_lock_path=self.rl,policy_path=self.po,execution_lock_path=self.el,audit_ledger_path=self.le,execution_plan_path=self.ep,recovery_snapshot_path=self.rs,dashboard_path=self.db,result_path=self.out,observed_at_override="2026-08-03T20:00:00+00:00",**k)
 def valid(self):
  w(self.ar,{"state":"SUPERVISED_REENTRY_READY","approval_id":"a1"})
  w(self.al,{"active":True,"approval_id":"a1","retry_plan_id":"r1","expires_at":"2026-08-03T21:00:00+00:00"})
  w(self.re,{"approval_id":"a1","retry_plan_id":"r1","action":"SUPERVISED_TRIGGER_REENTRY"})
  w(self.rp,{"retry_plan_id":"r1","trigger_id":"t1"})
  w(self.rl,{"active":True,"retry_plan_id":"r1"})
 def test_wait(self): self.assertEqual(self.run_stage()["state"],"REENTRY_EXECUTION_GUARD_WAIT_APPROVAL")
 def test_valid(self): self.valid(); x=self.run_stage(prepare_execution=True); self.assertEqual(x["state"],"REENTRY_EXECUTION_DRY_RUN_READY")
 def test_duplicate(self): self.valid(); w(self.el,{"active":True,"guard_id":"g"}); self.assertEqual(self.run_stage(prepare_execution=True)["status"],"BLOCKED")
 def test_expired(self): self.valid(); x=json.loads(self.al.read_text()); x["expires_at"]="2026-08-03T19:00:00+00:00"; w(self.al,x); self.assertEqual(self.run_stage(prepare_execution=True)["status"],"BLOCKED")
 def test_mismatch(self): self.valid(); x=json.loads(self.re.read_text()); x["retry_plan_id"]="bad"; w(self.re,x); self.assertEqual(self.run_stage(prepare_execution=True)["status"],"BLOCKED")
 def test_broker(self): x=json.loads(self.po.read_text()); x["broker_write_enabled"]=True; w(self.po,x); self.assertEqual(self.run_stage()["status"],"BLOCKED")
if __name__=="__main__": unittest.main()
