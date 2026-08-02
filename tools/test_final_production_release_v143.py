import json,tempfile,unittest
from pathlib import Path
from autonomous_paper_runtime.final_production_release import FinalProductionRelease
class Tests(unittest.TestCase):
 def w(self,p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v),encoding="utf-8")
 def data(self):
  scheduled={"status":"PASS","state":"AUTONOMOUS_RUNTIME_SCHEDULE_READY","scheduled_runtime_ready":True,"scheduled_runtime_id":"sched-1","runtime_id":"runtime-1","safe_mode_engaged":False}
  token={"scheduled_runtime_id":"sched-1","scheduled_runtime_ready":True,"continuous_loop_enabled":False,"actual_submission_allowed":False,"broker_network_allowed":False,"live_trading_enabled":False}
  deployment={"windows_task_reviewed":True,"service_account_reviewed":True,"log_rotation_ready":True,"monitoring_ready":True,"secret_storage_safe":True,"paper_endpoint_verified":True,"live_endpoint_blocked":True,"emergency_stop_ready":True}
  rollback={"rollback_script_ready":True,"configuration_backup_ready":True,"token_revocation_ready":True,"scheduled_task_disable_ready":True,"post_rollback_verification_ready":True}
  installer={"installer_script_ready":True,"install_check_ready":True,"verify_script_ready":True,"runbook_ready":True,"checksum_ready":True,"uninstaller_ready":True}
  return scheduled,token,deployment,rollback,installer
 def run_case(self,v):
  td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);root=Path(td.name)
  names=["scheduled","token","deployment","rollback","installer"];ps={n:root/f"{n}.json" for n in names}
  for n,x in zip(names,v):
   if x is not None:self.w(ps[n],x)
  result=FinalProductionRelease().run(
   scheduled_result_path=ps["scheduled"],scheduled_token_path=ps["token"],
   deployment_snapshot_path=ps["deployment"],rollback_snapshot_path=ps["rollback"],
   installer_snapshot_path=ps["installer"],production_certificate_path=root/"cert.json",
   deployment_manifest_path=root/"deploy.json",rollback_manifest_path=root/"rollback_out.json",
   final_token_path=root/"token_out.json",result_path=root/"result.json")
  return result,root
 def test_wait(self):
  v=list(self.data());v[0]={"status":"PASS","state":"WAIT_AUTONOMOUS_PAPER_RUNTIME","scheduled_runtime_ready":False,"safe_mode_engaged":False}
  self.assertEqual(self.run_case(v)[0]["state"],"WAIT_SCHEDULED_RUNTIME")
 def test_ready(self):
  r,root=self.run_case(self.data());self.assertEqual(r["state"],"V143_FINAL_PRODUCTION_PACKAGE_READY");self.assertTrue((root/"token_out.json").exists())
 def test_live_endpoint_blocks(self):
  v=list(self.data());v[2]=dict(v[2]);v[2]["live_endpoint_blocked"]=False;self.assertEqual(self.run_case(v)[0]["status"],"BLOCKED")
 def test_secret_storage_blocks(self):
  v=list(self.data());v[2]=dict(v[2]);v[2]["secret_storage_safe"]=False;self.assertEqual(self.run_case(v)[0]["status"],"BLOCKED")
 def test_rollback_blocks(self):
  v=list(self.data());v[3]=dict(v[3]);v[3]["rollback_script_ready"]=False;self.assertEqual(self.run_case(v)[0]["status"],"BLOCKED")
 def test_installer_blocks(self):
  v=list(self.data());v[4]=dict(v[4]);v[4]["checksum_ready"]=False;self.assertEqual(self.run_case(v)[0]["status"],"BLOCKED")
if __name__=="__main__":unittest.main()
