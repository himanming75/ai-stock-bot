import json,tempfile,unittest
from pathlib import Path
from autonomous_paper_runtime.weekly_observation_review import WeeklyObservationReview
class Tests(unittest.TestCase):
 def w(self,p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v),encoding="utf-8")
 def data(self):
  daily={"status":"PASS","state":"DAILY_READ_ONLY_OBSERVATION_READY","daily_read_only_observation_ready":True,"pilot_id":"pilot-1","safe_mode_engaged":False}
  policy={"review_id":"review-1","read_only":True,"order_submission_enabled":False,"live_trading_enabled":False,"minimum_observation_days":5,"minimum_stability_score":90,"max_abs_equity_drift":1000,"max_abs_cash_drift":1000}
  evidence={"days":[{"network_failures":0,"snapshot_failures":0,"unexpected_orders":0,"unexpected_positions":0,"risk_violations":0,"account_blocked_events":0,"trading_blocked_events":0,"equity_drift":0,"cash_drift":0} for _ in range(5)]}
  return daily,policy,evidence
 def run_case(self,v):
  td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);root=Path(td.name)
  names=["daily","policy","evidence"];ps={n:root/f"{n}.json" for n in names}
  for n,x in zip(names,v):
   if x is not None:self.w(ps[n],x)
  out=WeeklyObservationReview().run(daily_result_path=ps["daily"],weekly_evidence_path=ps["evidence"],review_policy_path=ps["policy"],weekly_summary_path=root/"summary.json",alert_report_path=root/"alerts.json",stability_score_path=root/"score.json",continuation_decision_path=root/"decision.json",review_token_path=root/"token.json",result_path=root/"result.json")
  return out,root
 def test_wait_before_daily(self):
  d,p,e=self.data();d={"status":"PASS","state":"WAIT_PAPER_OPERATIONS_PILOT","daily_read_only_observation_ready":False,"safe_mode_engaged":False}
  self.assertEqual(self.run_case((d,p,e))[0]["state"],"WAIT_DAILY_READ_ONLY_OBSERVATION")
 def test_weekly_ready(self):
  r,root=self.run_case(self.data());self.assertEqual(r["state"],"WEEKLY_PILOT_REVIEW_READY");self.assertEqual(r["stability_score"],100);self.assertTrue((root/"token.json").exists())
 def test_insufficient_days_blocks(self):
  d,p,e=self.data();e={"days":e["days"][:4]};self.assertEqual(self.run_case((d,p,e))[0]["status"],"BLOCKED")
 def test_unexpected_order_holds(self):
  d,p,e=self.data();e=json.loads(json.dumps(e));e["days"][0]["unexpected_orders"]=1
  r,_=self.run_case((d,p,e));self.assertFalse(r["pilot_continuation_allowed"])
 def test_blocked_account_holds(self):
  d,p,e=self.data();e=json.loads(json.dumps(e));e["days"][0]["account_blocked_events"]=1
  r,_=self.run_case((d,p,e));self.assertFalse(r["pilot_continuation_allowed"])
 def test_submission_policy_blocks(self):
  d,p,e=self.data();p=dict(p);p["order_submission_enabled"]=True;self.assertEqual(self.run_case((d,p,e))[0]["status"],"BLOCKED")
if __name__=="__main__":unittest.main()
