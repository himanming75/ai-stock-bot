import json,tempfile,unittest
from pathlib import Path
from shadow_trading.execution_engine_v81_05_08 import run_shadow_execution
class Tests(unittest.TestCase):
 def wr(self,p,d): p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(d),encoding="utf-8")
 def case(self,ready=True,action="BUY",qty=2,price=100,maxq=100):
  t=tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup); r=Path(t.name)
  self.wr(r/"f.json",{"state":"SHADOW_TRADING_READY" if ready else "WAIT_PAPER_TRADING_COMPLETION"}); self.wr(r/"o.json",{"symbol":"AAPL","shadow_action":action,"quantity":qty,"reference_price":price,"observed_at":"x"}); self.wr(r/"p.json",{"shadow_only":True,"broker_write_enabled":False,"live_trading_enabled":False,"fixed_slippage_bps":5,"commission_per_share":0.01,"minimum_commission":0,"maximum_quantity":maxq})
  x=run_shadow_execution(r/"f.json",r/"o.json",r/"p.json",r/"orders.jsonl",r/"fills.jsonl",r/"report.json",r/"dash.json",r/"result.json"); return x,r
 def test_wait(self): self.assertEqual(self.case(False)[0]["state"],"WAIT_SHADOW_TRADING_FOUNDATION")
 def test_hold(self): self.assertEqual(self.case(True,"HOLD",0)[0]["state"],"SHADOW_EXECUTION_NO_ACTION")
 def test_fill(self):
  x,r=self.case(); self.assertEqual(x["state"],"SHADOW_EXECUTION_FILLED"); self.assertTrue((r/"orders.jsonl").exists()); self.assertTrue((r/"fills.jsonl").exists())
 def test_buy_slippage(self): self.assertEqual(self.case()[0]["virtual_fill_price"],100.05)
 def test_sell_slippage(self): self.assertEqual(self.case(True,"SELL")[0]["virtual_fill_price"],99.95)
 def test_commission(self): self.assertEqual(self.case()[0]["commission"],0.02)
 def test_quantity_gate(self): self.assertEqual(self.case(qty=101,maxq=100)[0]["status"],"BLOCKED")
 def test_read_only(self):
  x,_=self.case(); self.assertFalse(x["broker_write_enabled"]); self.assertEqual(x["network_requests_executed"],0); self.assertEqual(x["actual_paper_orders_submitted"],0)
if __name__=="__main__": unittest.main()
