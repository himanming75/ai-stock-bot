import json,tempfile,unittest
from pathlib import Path
from autonomous_paper_runtime.automatic_snapshot_collector import AutomaticSnapshotCollector,LIVE_BASE_URL

class Tests(unittest.TestCase):
 def w(self,p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v),encoding="utf-8")
 def data(self):
  weekly={"status":"PASS","state":"WEEKLY_PILOT_REVIEW_READY","weekly_review_ready":True,"pilot_continuation_allowed":True,"pilot_id":"pilot-1","safe_mode_engaged":False}
  policy={"collector_id":"collector-1","read_only":True,"order_submission_enabled":False,"live_trading_enabled":False,"rotation_enabled":True,"history_limit":3,"expected_base_url":"https://paper-api.alpaca.markets"}
  fixture={"account":{"status":"ACTIVE","account_blocked":False,"trading_blocked":False,"equity":"100000","cash":"100000"},"clock":{"is_open":False},"open_orders":[],"positions":[]}
  return weekly,policy,fixture
 def run_case(self,v,base_url="https://paper-api.alpaca.markets",preexisting=False):
  td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);root=Path(td.name)
  weekly,policy,fixture=v
  self.w(root/"weekly.json",weekly)
  if policy is not None:self.w(root/"policy.json",policy)
  if fixture is not None:self.w(root/"fixture.json",fixture)
  if preexisting:self.w(root/"current.json",fixture)
  out=AutomaticSnapshotCollector().run(
   weekly_review_path=root/"weekly.json",collector_policy_path=root/"policy.json",
   fixture_snapshot_path=root/"fixture.json",previous_snapshot_path=root/"previous.json",
   current_snapshot_path=root/"current.json",history_dir=root/"history",
   rotation_report_path=root/"rotation.json",collector_token_path=root/"token.json",
   result_path=root/"result.json",base_url=base_url,enable_network=False)
  return out,root
 def test_wait_before_weekly(self):
  w,p,f=self.data();w={"status":"PASS","state":"WAIT_DAILY_READ_ONLY_OBSERVATION","weekly_review_ready":False,"pilot_continuation_allowed":False,"safe_mode_engaged":False}
  self.assertEqual(self.run_case((w,p,f))[0]["state"],"WAIT_WEEKLY_PILOT_REVIEW")
 def test_local_collection_ready(self):
  r,root=self.run_case(self.data());self.assertEqual(r["state"],"AUTOMATIC_SNAPSHOT_COLLECTION_READY");self.assertTrue((root/"current.json").exists());self.assertTrue((root/"token.json").exists())
 def test_rotation(self):
  r,root=self.run_case(self.data(),preexisting=True);self.assertTrue(r["previous_snapshot_rotated"]);self.assertTrue((root/"previous.json").exists())
 def test_live_endpoint_blocks(self):
  self.assertEqual(self.run_case(self.data(),base_url=LIVE_BASE_URL)[0]["status"],"BLOCKED")
 def test_submission_policy_blocks(self):
  w,p,f=self.data();p=dict(p);p["order_submission_enabled"]=True;self.assertEqual(self.run_case((w,p,f))[0]["status"],"BLOCKED")
 def test_blocked_account_blocks(self):
  w,p,f=self.data();f=json.loads(json.dumps(f));f["account"]["account_blocked"]=True;self.assertEqual(self.run_case((w,p,f))[0]["status"],"BLOCKED")
if __name__=="__main__":unittest.main()
