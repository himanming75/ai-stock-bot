import unittest
from tools.paper_portfolio_update_v59_0 import *
def exe(action="BUY",q="100",p="200.20",status="PASS",state="FILLED"):
 return {"status":status,"final_state":state,"symbol":"AAPL","action":action,"filled_quantity":q,"average_fill_price":p,"execution_sha256":"a"*64,"network_used":False}
def acct(cash="50000",positions=None,equity="50000",commission="0"):
 return {"cash":cash,"equity":equity,"initial_equity":"50000","positions":positions or [],"commission_per_trade":commission,"network_used":False}
class T(unittest.TestCase):
 def go(self,e=None,s=None,prices=None):
  return PaperPortfolioUpdateV590().update(e or exe(),s or acct(),market_prices=prices or {"AAPL":"205"},snapshot_time="2026-07-29T21:00:00Z")
 def test_buy_open(self): self.assertEqual("100",self.go()["reconciliation"]["positions"][0]["quantity"])
 def test_cash(self): self.assertEqual("29980.0000",self.go()["reconciliation"]["ending_cash"])
 def test_equity(self): self.assertEqual("50480.0000",self.go()["reconciliation"]["total_equity"])
 def test_avg(self): self.assertEqual("200.2000",self.go()["reconciliation"]["positions"][0]["average_cost"])
 def test_unreal(self): self.assertEqual("480.0000",self.go()["reconciliation"]["positions"][0]["unrealized_pnl"])
 def test_buy_add(self):
  s=acct(positions=[{"symbol":"AAPL","quantity":"50","average_cost":"190","realized_pnl":"0","total_commission":"0"}])
  self.assertEqual("150",self.go(s=s)["reconciliation"]["positions"][0]["quantity"])
 def test_sell_partial(self):
  s=acct(positions=[{"symbol":"AAPL","quantity":"100","average_cost":"190","realized_pnl":"0","total_commission":"0"}])
  x=self.go(exe("SELL","40","205"),s); self.assertEqual("60",x["reconciliation"]["positions"][0]["quantity"])
 def test_sell_close(self):
  s=acct(positions=[{"symbol":"AAPL","quantity":"100","average_cost":"190","realized_pnl":"0","total_commission":"0"}])
  self.assertEqual(0,self.go(exe("SELL","100","205"),s)["reconciliation"]["position_count"])
 def test_realized(self):
  s=acct(positions=[{"symbol":"AAPL","quantity":"100","average_cost":"190","realized_pnl":"0","total_commission":"0"}])
  self.assertEqual("600.0000",self.go(exe("SELL","40","205"),s)["reconciliation"]["total_realized_pnl"])
 def test_commission(self): self.assertEqual("29979.0000",self.go(s=acct(commission="1"))["reconciliation"]["ending_cash"])
 def test_insufficient(self):
  with self.assertRaises(ValueError): self.go(s=acct(cash="10"))
 def test_oversell(self):
  s=acct(positions=[{"symbol":"AAPL","quantity":"10","average_cost":"190"}])
  with self.assertRaises(ValueError): self.go(exe("SELL","20"),s)
 def test_sell_none(self):
  with self.assertRaises(ValueError): self.go(exe("SELL"))
 def test_zero_qty(self):
  with self.assertRaises(ValueError): self.go(exe(q="0"))
 def test_bad_price(self):
  with self.assertRaises(ValueError): self.go(exe(p="-1"))
 def test_bad_action(self):
  with self.assertRaises(ValueError): self.go(exe("HOLD"))
 def test_bad_status(self):
  with self.assertRaises(ValueError): self.go(exe(status="FAIL"))
 def test_bad_final(self):
  with self.assertRaises(ValueError): self.go(exe(state="REJECTED"))
 def test_network_execution(self):
  e=exe();e["network_used"]=True
  with self.assertRaises(ValueError): self.go(e=e)
 def test_missing_market(self):
  with self.assertRaises(ValueError): self.go(prices={"MSFT":"1"})
 def test_hash(self): self.assertEqual(64,len(self.go()["integration_sha256"]))
 def test_position_hash(self): self.assertEqual(64,len(self.go()["reconciliation"]["positions"][0]["position_sha256"]))
 def test_snapshot_hash(self): self.assertEqual(64,len(self.go()["snapshot"]["snapshot_sha256"]))
 def test_event_open(self): self.assertEqual("POSITION_OPENED",self.go()["reconciliation"]["ledger"][0]["event_type"])
 def test_event_increase(self):
  s=acct(positions=[{"symbol":"AAPL","quantity":"1","average_cost":"190"}])
  self.assertEqual("POSITION_INCREASED",self.go(s=s)["reconciliation"]["ledger"][0]["event_type"])
 def test_event_reduce(self):
  s=acct(positions=[{"symbol":"AAPL","quantity":"100","average_cost":"190"}])
  self.assertEqual("POSITION_REDUCED",self.go(exe("SELL","1"),s)["reconciliation"]["ledger"][0]["event_type"])
 def test_event_close(self):
  s=acct(positions=[{"symbol":"AAPL","quantity":"100","average_cost":"190"}])
  self.assertEqual("POSITION_CLOSED",self.go(exe("SELL","100"),s)["reconciliation"]["ledger"][0]["event_type"])
 def test_live_block(self):
  with self.assertRaises(PermissionError): PaperPortfolioUpdateV590(mode="live").update(exe(),acct(),market_prices={"AAPL":"1"},snapshot_time="2026-01-01T00:00:00Z")
 def test_live_unimplemented(self):
  with self.assertRaises(NotImplementedError): PaperPortfolioUpdateV590(mode="live",enable_live=True).update(exe(),acct(),market_prices={"AAPL":"1"},snapshot_time="2026-01-01T00:00:00Z")
 def test_prices(self): self.assertEqual({"AAPL":"205","MSFT":"400"},parse_prices("AAPL=205,MSFT=400"))
 def test_deterministic(self): self.assertEqual(self.go()["integration_sha256"],self.go()["integration_sha256"])
 def test_snapshot_count(self): self.assertEqual(1,self.go()["snapshot"]["position_count"])
if __name__=="__main__": unittest.main()
