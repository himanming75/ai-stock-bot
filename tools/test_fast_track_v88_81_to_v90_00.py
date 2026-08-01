
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.fast_track_v88_81_v90_00 import *

class T(unittest.TestCase):
 def setUp(self): self.c=FastTrackConfig()
 def test_config(self): self.c.validate()
 def test_unsafe_scheduler(self):
  with self.assertRaises(ValueError): FastTrackConfig(scheduler_enabled=True).validate()
 def test_unsafe_submit(self):
  with self.assertRaises(ValueError): FastTrackConfig(paper_order_submission_authorized=True).validate()
 def test_portfolio(self): self.assertEqual(portfolio_state(self.c)["cash"],100000.0)
 def test_reserve(self): self.assertEqual(reserve_cash(portfolio_state(self.c),200)["available_cash"],99800.0)
 def test_fill(self):
  s=apply_fill(portfolio_state(self.c),"AAPL",1,200);self.assertEqual(s["cash"],99800.0)
 def test_mark(self):
  s=apply_fill(portfolio_state(self.c),"AAPL",1,200);m=mark_to_market(s,{"AAPL":201})
  self.assertEqual(m["unrealized_pnl"],1.0)
 def test_reconcile(self):
  b=portfolio_state(self.c);a=apply_fill(b,"AAPL",1,200)
  self.assertEqual(reconcile_portfolio(b,a,{"symbol":"AAPL","qty":1,"price":200})["status"],"PASS")
 def test_exposure(self):
  s=mark_to_market(apply_fill(portfolio_state(self.c),"AAPL",1,200),{"AAPL":201})
  self.assertGreater(exposure_metrics(self.c,s)["total_exposure_pct"],0)
 def test_risk_pass(self):
  self.assertEqual(pretrade_risk(self.c,portfolio_state(self.c),{"symbol":"AAPL","qty":1,"price":200})["status"],"PASS")
 def test_notional_fail(self):
  self.assertEqual(pretrade_risk(self.c,portfolio_state(self.c),{"symbol":"AAPL","qty":10,"price":200})["status"],"FAIL")
 def test_daily_loss_fail(self):
  self.assertEqual(pretrade_risk(self.c,portfolio_state(self.c),{"symbol":"AAPL","qty":1,"price":200},daily_pnl=-600)["status"],"FAIL")
 def test_drawdown_fail(self):
  s=portfolio_state(self.c);s["equity"]=90000
  self.assertEqual(pretrade_risk(self.c,s,{"symbol":"AAPL","qty":1,"price":200},peak_equity=100000)["status"],"FAIL")
 def test_kill(self): self.assertTrue(kill_switch(True,"x")["triggered"])
 def test_cycle(self):
  i={"signal_id":"s","symbol":"AAPL","qty":1,"price":200}
  self.assertEqual(runtime_cycle(self.c,portfolio_state(self.c),i,set())["status"],"PASS")
 def test_duplicate(self):
  i={"signal_id":"s","symbol":"AAPL","qty":1,"price":200}
  self.assertEqual(runtime_cycle(self.c,portfolio_state(self.c),i,{"s"})["status"],"SKIP")
 def test_replay(self): self.assertEqual(replay(self.c)["status"],"PASS")
 def test_rollback(self): self.assertEqual(rollback_package()["status"],"PASS")
 def test_simulation(self): self.assertEqual(integrated_simulation(self.c)["status"],"PASS")
 def test_store(self):
  with TemporaryDirectory() as t:
   pid,_=store(Path(t),{"x":{"a":1}});self.assertTrue(pid.startswith("paper-runtime-rc1-"))
 def test_manifest(self):
  with TemporaryDirectory() as t:
   o=Path(t);_,l=store(o,{"x":{"a":1}});self.assertEqual(manifest(o,l)["status"],"PASS")

if __name__=="__main__": unittest.main()
