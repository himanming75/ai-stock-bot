import json,tempfile,unittest
from pathlib import Path
from autonomous_paper_runtime.automatic_shadow_signal_pipeline import AutomaticShadowSignalPipeline
class Tests(unittest.TestCase):
 def w(self,p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v),encoding="utf-8")
 def data(self):
  source={"status":"PASS","state":"MULTI_DAY_SHADOW_VALIDATION_READY","multi_day_shadow_validation_ready":True,"shadow_continuation_allowed":True,"shadow_session_id":"shadow-1","safe_mode_engaged":False}
  policy={"pipeline_id":"pipeline-1","shadow_only":True,"order_submission_enabled":False,"broker_write_enabled":False,"live_trading_enabled":False,"max_queue_size":10,"minimum_confidence":0.7,"allowed_actions":["BUY","SELL","HOLD"]}
  market={"symbol":"AAPL","reference_price":100,"market_open":True,"as_of":"2026-08-02T06:40:00Z","stale":False}
  strategy={"action":"BUY","confidence":0.85,"quantity":2,"strategy_verified":True}
  return source,policy,market,strategy
 def run_case(self,v):
  td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);root=Path(td.name)
  names=["source","policy","market","strategy"];ps={n:root/f"{n}.json" for n in names}
  for n,x in zip(names,v):
   if x is not None:self.w(ps[n],x)
  out=AutomaticShadowSignalPipeline().run(validation_result_path=ps["source"],pipeline_policy_path=ps["policy"],market_snapshot_path=ps["market"],strategy_snapshot_path=ps["strategy"],generated_signal_path=root/"signal.json",signal_queue_path=root/"queue.jsonl",validation_report_path=root/"validation.json",handoff_token_path=root/"token.json",result_path=root/"result.json")
  return out,root
 def test_wait_before_validation(self):
  s,p,m,t=self.data();s={"status":"PASS","state":"WAIT_SHADOW_PERFORMANCE","multi_day_shadow_validation_ready":False,"shadow_continuation_allowed":False,"safe_mode_engaged":False}
  self.assertEqual(self.run_case((s,p,m,t))[0]["state"],"WAIT_MULTI_DAY_SHADOW_VALIDATION")
 def test_buy_pipeline_ready(self):
  r,root=self.run_case(self.data());self.assertEqual(r["state"],"AUTOMATIC_SHADOW_SIGNAL_PIPELINE_READY");self.assertEqual(r["approved_action"],"BUY");self.assertTrue((root/"queue.jsonl").exists())
 def test_market_closed_becomes_hold(self):
  s,p,m,t=self.data();m=dict(m);m["market_open"]=False
  r,_=self.run_case((s,p,m,t));self.assertEqual(r["approved_action"],"HOLD");self.assertIn("MARKET_CLOSED",r["pipeline_reasons"])
 def test_low_confidence_becomes_hold(self):
  s,p,m,t=self.data();t=dict(t);t["confidence"]=0.5
  r,_=self.run_case((s,p,m,t));self.assertEqual(r["approved_action"],"HOLD")
 def test_stale_market_blocks(self):
  s,p,m,t=self.data();m=dict(m);m["stale"]=True
  self.assertEqual(self.run_case((s,p,m,t))[0]["status"],"BLOCKED")
 def test_submission_policy_blocks(self):
  s,p,m,t=self.data();p=dict(p);p["order_submission_enabled"]=True
  self.assertEqual(self.run_case((s,p,m,t))[0]["status"],"BLOCKED")
if __name__=="__main__":unittest.main()
