import json,tempfile,unittest
from pathlib import Path
from shadow_trading.foundation_v81 import run_shadow_foundation
class Tests(unittest.TestCase):
 def write(self,p,d): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(d),encoding="utf-8")
 def case(self,complete=False,snapshot=True):
  td=tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup); r=Path(td.name)
  self.write(r/"policy.json",{"paper_only":True,"broker_write_enabled":False,"live_trading_enabled":False}); self.write(r/"completion.json",{"completion_ready":complete})
  if snapshot:self.write(r/"snapshot.json",{"account":{"status":"ACTIVE","portfolio_value":"100000"},"positions":[],"open_orders":[]})
  self.write(r/"signal.json",{"symbol":"AAPL","approved_action":"BUY","quantity":1,"reference_price":200})
  x=run_shadow_foundation(r/"completion.json",r/"snapshot.json",r/"signal.json",r/"policy.json",r/"result.json",r/"dashboard.json",r/"observation.json"); return x,r
 def test_wait_completion(self): self.assertEqual(self.case(False,True)[0]["state"],"WAIT_PAPER_TRADING_COMPLETION")
 def test_wait_snapshot(self): self.assertEqual(self.case(True,False)[0]["state"],"WAIT_ACCOUNT_SNAPSHOT")
 def test_shadow_ready(self): self.assertEqual(self.case(True,True)[0]["state"],"SHADOW_TRADING_READY")
 def test_observation_written(self): x,r=self.case(True,True); self.assertTrue(x["shadow_observation_written"] and (r/"observation.json").exists())
 def test_dashboard_written(self): x,r=self.case(True,True); self.assertTrue(x["dashboard_state_written"] and (r/"dashboard.json").exists())
 def test_read_only_contract(self): x,_=self.case(True,True); self.assertFalse(x["broker_write_enabled"]); self.assertEqual(x["network_requests_executed"],0); self.assertEqual(x["write_requests_executed"],0)
if __name__=="__main__": unittest.main()
