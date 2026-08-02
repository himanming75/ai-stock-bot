import json,tempfile,unittest
from pathlib import Path
from autonomous_paper_runtime.windows_scheduled_read_only_collection import WindowsScheduledReadOnlyCollection

class Tests(unittest.TestCase):
 def w(self,p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v),encoding="utf-8")
 def data(self):
  collector={"status":"PASS","state":"AUTOMATIC_SNAPSHOT_COLLECTION_READY","automatic_snapshot_collector_ready":True,"collector_id":"collector-1","pilot_id":"pilot-1","safe_mode_engaged":False}
  policy={"schedule_id":"schedule-1","task_name":"AIStockBot-ReadOnly-Collector","read_only":True,"order_submission_enabled":False,"live_trading_enabled":False,"network_write_enabled":False,"interval_minutes":15,"max_retries":3,"auto_install_task":False}
  recovery={"recovery_required":False,"active_task_instances":0,"snapshot_write_in_progress":False,"current_snapshot_corrupted":False,"credentials_available":True,"recovery_verified":True}
  return collector,policy,recovery
 def run_case(self,v):
  td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);root=Path(td.name)
  names=["collector","policy","recovery"];ps={n:root/f"{n}.json" for n in names}
  for n,x in zip(names,v):
   if x is not None:self.w(ps[n],x)
  out=WindowsScheduledReadOnlyCollection().run(
   collector_result_path=ps["collector"],schedule_policy_path=ps["policy"],
   recovery_snapshot_path=ps["recovery"],task_plan_path=root/"plan.json",
   heartbeat_path=root/"heartbeat.json",recovery_report_path=root/"recovery_report.json",
   schedule_token_path=root/"token.json",result_path=root/"result.json")
  return out,root
 def test_wait_before_collector(self):
  c,p,r=self.data();c={"status":"PASS","state":"WAIT_WEEKLY_PILOT_REVIEW","automatic_snapshot_collector_ready":False,"safe_mode_engaged":False}
  self.assertEqual(self.run_case((c,p,r))[0]["state"],"WAIT_AUTOMATIC_SNAPSHOT_COLLECTOR")
 def test_plan_ready(self):
  r,root=self.run_case(self.data());self.assertEqual(r["state"],"WINDOWS_SCHEDULED_READ_ONLY_PLAN_READY");self.assertTrue((root/"plan.json").exists());self.assertFalse(r["task_installed"])
 def test_auto_install_blocks(self):
  c,p,r=self.data();p=dict(p);p["auto_install_task"]=True;self.assertEqual(self.run_case((c,p,r))[0]["status"],"BLOCKED")
 def test_network_write_blocks(self):
  c,p,r=self.data();p=dict(p);p["network_write_enabled"]=True;self.assertEqual(self.run_case((c,p,r))[0]["status"],"BLOCKED")
 def test_duplicate_instance_blocks(self):
  c,p,r=self.data();r=dict(r);r["active_task_instances"]=2;self.assertEqual(self.run_case((c,p,r))[0]["status"],"BLOCKED")
 def test_corrupted_snapshot_blocks(self):
  c,p,r=self.data();r=dict(r);r["current_snapshot_corrupted"]=True;self.assertEqual(self.run_case((c,p,r))[0]["status"],"BLOCKED")
if __name__=="__main__":unittest.main()
