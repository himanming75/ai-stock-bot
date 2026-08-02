import json,tempfile,unittest
from pathlib import Path
from autonomous_paper_runtime.autonomous_engine_bundle import AutonomousEngineBundle
class T(unittest.TestCase):
 def w(self,p,v): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v),encoding="utf-8")
 def data(self):
  return (
   {"status":"PASS","state":"RUNTIME_CONTROL_READY","runtime_control_ready":True,"runtime_cycle_id":"runtime-1","safe_mode_engaged":False},
   {"runtime_cycle_id":"runtime-1","runtime_control_ready":True},
   {"signal_id":"sig-1","symbol":"SPY","side":"BUY","confidence":0.9,"minimum_confidence":0.7,"entry_price":100,"stop_price":98},
   {"equity":10000,"buying_power":5000,"risk_per_trade_pct":0.01,"max_symbol_exposure":2000},
   {"unresolved_submission":False,"active_order_present":False,"state_corrupted":False,"recovery_verified":True},
   {"enabled":True,"interval_seconds":30,"heartbeat_age_seconds":2,"max_heartbeat_age_seconds":120,"scheduler_process_count":1})
 def run_case(self,vals):
  td=tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup); r=Path(td.name)
  names=["control","token","signal","account","recovery","scheduler"]; ps={n:r/f"{n}.json" for n in names}
  for n,v in zip(names,vals):
   if v is not None:self.w(ps[n],v)
  return AutonomousEngineBundle().run(control_result_path=ps["control"],control_token_path=ps["token"],
   signal_path=ps["signal"],account_path=ps["account"],recovery_path=ps["recovery"],scheduler_path=ps["scheduler"],
   order_candidate_path=r/"candidate.json",recovery_token_path=r/"recovery_token.json",heartbeat_path=r/"heartbeat.json",
   engine_token_path=r/"engine.json",result_path=r/"result.json")
 def test_wait(self):
  v=list(self.data());v[0]={"status":"PASS","state":"WAIT_RUNTIME_READY","runtime_control_ready":False,"safe_mode_engaged":False}
  self.assertEqual(self.run_case(v)["state"],"WAIT_RUNTIME_CONTROL")
 def test_ready(self): self.assertEqual(self.run_case(self.data())["state"],"AUTONOMOUS_ENGINE_READY")
 def test_low_confidence(self):
  v=list(self.data());v[2]=dict(v[2]);v[2]["confidence"]=0.1;self.assertEqual(self.run_case(v)["status"],"BLOCKED")
 def test_zero_size(self):
  v=list(self.data());v[3]=dict(v[3]);v[3]["buying_power"]=1;self.assertEqual(self.run_case(v)["status"],"BLOCKED")
 def test_recovery_blocks(self):
  v=list(self.data());v[4]=dict(v[4]);v[4]["active_order_present"]=True;self.assertEqual(self.run_case(v)["status"],"BLOCKED")
 def test_scheduler_blocks(self):
  v=list(self.data());v[5]=dict(v[5]);v[5]["enabled"]=False;self.assertEqual(self.run_case(v)["status"],"BLOCKED")
if __name__=="__main__":unittest.main()
