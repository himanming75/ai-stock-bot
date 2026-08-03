import json,tempfile,unittest
from pathlib import Path
from paper_runtime.retry_approval_supervised_reentry_v83_41_44 import run_retry_approval_supervised_reentry
def w(p,x): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(x),encoding="utf-8")
class T(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(); self.r=Path(self.t.name)
  self.rr=self.r/"rr.json"; self.rp=self.r/"rp.json"; self.rl=self.r/"rl.json"; self.pol=self.r/"pol.json"
  self.al=self.r/"al.json"; self.led=self.r/"led.jsonl"; self.re=self.r/"re.json"; self.d=self.r/"d.json"; self.o=self.r/"o.json"
  w(self.pol,{"paper_only":True,"approval_ttl_seconds":300,"broker_write_enabled":False,"order_submission_enabled":False,"live_trading_enabled":False,"external_network_enabled":False,"automatic_reentry_execution_enabled":False})
 def tearDown(self): self.t.cleanup()
 def run_stage(self,**k): return run_retry_approval_supervised_reentry(retry_policy_result_path=self.rr,retry_plan_path=self.rp,retry_lock_path=self.rl,approval_policy_path=self.pol,approval_lock_path=self.al,approval_ledger_path=self.led,reentry_plan_path=self.re,dashboard_path=self.d,result_path=self.o,observed_at_override="2026-08-03T20:00:00+00:00",**k)
 def setup_plan(self):
  w(self.rr,{"state":"TRIGGER_RETRY_PLANNED"}); w(self.rp,{"retry_plan_id":"rp1","trigger_id":"t1"}); w(self.rl,{"active":True,"retry_plan_id":"rp1"})
 def test_wait(self): self.assertEqual(self.run_stage()["state"],"RETRY_APPROVAL_WAIT_PLAN")
 def test_approve(self): self.setup_plan(); x=self.run_stage(approve_retry=True); self.assertEqual(x["state"],"SUPERVISED_REENTRY_READY")
 def test_duplicate(self): self.setup_plan(); w(self.al,{"active":True,"approval_id":"a"}); self.assertEqual(self.run_stage(approve_retry=True)["status"],"BLOCKED")
 def test_complete(self): self.setup_plan(); self.run_stage(approve_retry=True); x=self.run_stage(complete_reentry=True); self.assertEqual(x["state"],"SUPERVISED_REENTRY_COMPLETED")
 def test_missing_plan(self): w(self.rr,{"state":"TRIGGER_RETRY_PLANNED"}); self.assertEqual(self.run_stage(approve_retry=True)["status"],"BLOCKED")
 def test_broker_fail_closed(self):
  p=json.loads(self.pol.read_text()); p["broker_write_enabled"]=True; w(self.pol,p); self.assertEqual(self.run_stage()["status"],"BLOCKED")
if __name__=="__main__": unittest.main()
