import json,tempfile,unittest
from pathlib import Path
from autonomous_paper_runtime.multi_day_shadow_validation import MultiDayShadowValidation
class Tests(unittest.TestCase):
 def w(self,p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v),encoding="utf-8")
 def data(self):
  source={"status":"PASS","state":"SHADOW_PERFORMANCE_EVALUATION_READY","shadow_performance_evaluation_ready":True,"shadow_session_id":"shadow-1","safe_mode_engaged":False}
  policy={"validation_id":"validation-1","shadow_only":True,"order_submission_enabled":False,"live_trading_enabled":False,"minimum_trading_days":3,"minimum_signal_count":6,"minimum_signal_accuracy_pct":60,"minimum_risk_consistency_pct":90,"maximum_drawdown_pct":5,"minimum_profit_factor":1,"maximum_late_signals":0,"maximum_missed_signals":0,"maximum_risk_overrides":0,"maximum_emergency_stops":0}
  day={"signal_count":2,"correct_signal_count":2,"duplicate_signal_count":0,"late_signal_count":0,"missed_signal_count":0,"risk_decision_count":2,"consistent_risk_decision_count":2,"risk_override_count":0,"emergency_stop_count":0,"total_pnl":10,"max_drawdown_pct":1,"profit_factor":1.5}
  evidence={"days":[dict(day),dict(day),dict(day)]}
  return source,policy,evidence
 def run_case(self,v):
  td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);root=Path(td.name)
  names=["source","policy","evidence"];ps={n:root/f"{n}.json" for n in names}
  for n,x in zip(names,v):
   if x is not None:self.w(ps[n],x)
  out=MultiDayShadowValidation().run(performance_result_path=ps["source"],validation_policy_path=ps["policy"],multi_day_evidence_path=ps["evidence"],summary_path=root/"summary.json",signal_quality_path=root/"signal.json",risk_consistency_path=root/"risk.json",continuation_decision_path=root/"decision.json",validation_token_path=root/"token.json",result_path=root/"result.json")
  return out,root
 def test_wait_before_performance(self):
  s,p,e=self.data();s={"status":"PASS","state":"WAIT_SHADOW_DECISION","shadow_performance_evaluation_ready":False,"safe_mode_engaged":False}
  self.assertEqual(self.run_case((s,p,e))[0]["state"],"WAIT_SHADOW_PERFORMANCE")
 def test_validation_ready(self):
  r,root=self.run_case(self.data());self.assertEqual(r["state"],"MULTI_DAY_SHADOW_VALIDATION_READY");self.assertTrue(r["shadow_continuation_allowed"]);self.assertTrue((root/"token.json").exists())
 def test_insufficient_days_blocks(self):
  s,p,e=self.data();e={"days":e["days"][:2]};self.assertEqual(self.run_case((s,p,e))[0]["status"],"BLOCKED")
 def test_duplicate_signal_holds(self):
  s,p,e=self.data();e=json.loads(json.dumps(e));e["days"][0]["duplicate_signal_count"]=1
  r,_=self.run_case((s,p,e));self.assertFalse(r["shadow_continuation_allowed"])
 def test_risk_override_holds(self):
  s,p,e=self.data();e=json.loads(json.dumps(e));e["days"][0]["risk_override_count"]=1
  r,_=self.run_case((s,p,e));self.assertFalse(r["shadow_continuation_allowed"])
 def test_submission_policy_blocks(self):
  s,p,e=self.data();p=dict(p);p["order_submission_enabled"]=True
  self.assertEqual(self.run_case((s,p,e))[0]["status"],"BLOCKED")
if __name__=="__main__":unittest.main()
