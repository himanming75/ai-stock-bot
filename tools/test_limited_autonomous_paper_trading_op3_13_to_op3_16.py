import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from autonomous_paper_runtime.limited_autonomous_paper_trading import APPROVAL_PHRASE,LIVE_BASE_URL,LimitedAutonomousPaperTrading
class Tests(unittest.TestCase):
 def w(self,p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v),encoding="utf-8")
 def data(self):
  lifecycle={"paper_order_lifecycle_ready":True,"lifecycle_complete":True,"safe_mode_engaged":False}
  policy={"runtime_id":"runtime-1","paper_only":True,"single_cycle_only":True,"continuous_loop_enabled":False,"maximum_orders_per_cycle":1,"maximum_daily_orders":1,"maximum_order_notional":100,"maximum_open_positions":2,"maximum_daily_loss":50,"maximum_consecutive_losses":2,"market_close_buffer_minutes":15,"timeout_seconds":10,"live_trading_enabled":False,"expected_base_url":"https://paper-api.alpaca.markets"}
  signal={"signal_id":"sig-1","symbol":"AAPL","approved_action":"BUY","confidence":0.9,"quantity":1,"reference_price":50,"signal_verified":True}
  risk={"cycle_date":"2026-08-02","daily_orders":0,"open_positions":0,"daily_pnl":0,"consecutive_losses":0,"minutes_to_market_close":120,"emergency_stop_engaged":False,"duplicate_signal":False,"market_open":True}
  account={"account":{"status":"ACTIVE","account_blocked":False,"trading_blocked":False,"buying_power":"100000"}}
  return lifecycle,policy,signal,risk,account
 def run_case(self,vals,**kwargs):
  td=tempfile.TemporaryDirectory();self.addCleanup(td.cleanup);root=Path(td.name);names=["lifecycle","policy","signal","risk","account"];paths={n:root/f"{n}.json" for n in names}
  for n,v in zip(names,vals):self.w(paths[n],v)
  out=LimitedAutonomousPaperTrading().run(lifecycle_result_path=paths["lifecycle"],runtime_policy_path=paths["policy"],signal_snapshot_path=paths["signal"],risk_snapshot_path=paths["risk"],account_snapshot_path=paths["account"],runtime_state_path=root/"state.json",decision_path=root/"decision.json",submission_receipt_path=root/"receipt.json",runtime_ledger_path=root/"ledger.jsonl",completion_token_path=root/"token.json",result_path=root/"result.json",**kwargs)
  return out,root
 def test_default_armed_preview(self):
  r,_=self.run_case(self.data());self.assertEqual(r["state"],"LIMITED_AUTONOMOUS_PAPER_CYCLE_ARMED");self.assertEqual(r["actual_paper_orders_submitted"],0)
 def test_emergency_stop_holds(self):
  v=list(self.data());v[3]=dict(v[3]);v[3]["emergency_stop_engaged"]=True
  r,_=self.run_case(tuple(v));self.assertEqual(r["approved_action"],"HOLD");self.assertIn("EMERGENCY_STOP",r["risk_reasons"])
 def test_daily_loss_holds(self):
  v=list(self.data());v[3]=dict(v[3]);v[3]["daily_pnl"]=-50
  r,_=self.run_case(tuple(v));self.assertEqual(r["approved_action"],"HOLD")
 def test_live_endpoint_blocks(self):
  r,_=self.run_case(self.data(),base_url=LIVE_BASE_URL);self.assertEqual(r["status"],"BLOCKED")
 def test_prior_order_must_be_terminal(self):
  v=list(self.data());v[0]=dict(v[0]);v[0]["lifecycle_complete"]=False
  r,_=self.run_case(tuple(v));self.assertEqual(r["status"],"BLOCKED")
 def test_mock_single_submission(self):
  def transport(**kwargs):return 200,{"id":"paper-order-2","status":"accepted"}
  with patch.dict(os.environ,{"APCA_API_KEY_ID":"key","APCA_API_SECRET_KEY":"secret"},clear=False):
   r,root=self.run_case(self.data(),enable_network=True,enable_submission=True,approval_phrase=APPROVAL_PHRASE,transport=transport)
  self.assertEqual(r["actual_paper_orders_submitted"],1);self.assertEqual(r["live_orders_submitted"],0);self.assertTrue((root/"ledger.jsonl").exists())
if __name__=="__main__":unittest.main()
