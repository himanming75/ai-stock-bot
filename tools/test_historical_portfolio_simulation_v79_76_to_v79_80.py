from pathlib import Path
from tempfile import TemporaryDirectory
import json,unittest
from alpaca_market_data.historical_portfolio_simulation_v79_76_80 import *
def fixture():
 return [{"symbol":"AAPL","timeframe":"1Min","timestamp":"1","source_close":100,"signal":"BUY"},
 {"symbol":"AAPL","timeframe":"1Min","timestamp":"2","source_close":110,"signal":"HOLD"},
 {"symbol":"AAPL","timeframe":"1Min","timestamp":"3","source_close":120,"signal":"SELL"}]
class T(unittest.TestCase):
 def setUp(self): self.c=PortfolioConfig()
 def test_config(self): self.c.validate()
 def test_network(self):
  with self.assertRaises(ValueError): PortfolioConfig(allow_network=True).validate()
 def test_buy_sell(self):
  r=simulate_portfolio(fixture(),self.c); self.assertEqual(r["trade_count"],2); self.assertGreater(r["realized_pnl"],0)
 def test_hold_only(self):
  r=simulate_portfolio([{"symbol":"A","timeframe":"1","timestamp":"1","source_close":10,"signal":"HOLD"}],self.c)
  self.assertEqual(r["final_equity"],self.c.initial_cash)
 def test_no_short(self):
  r=simulate_portfolio([{"symbol":"A","timeframe":"1","timestamp":"1","source_close":10,"signal":"SELL"}],self.c)
  self.assertEqual(r["trade_count"],0)
 def test_validate(self): self.assertEqual(validate_simulation(simulate_portfolio(fixture(),self.c))["trade_count"],2)
 def test_bad_price(self):
  with self.assertRaises(ValueError): simulate_portfolio([{"symbol":"A","timeframe":"1","timestamp":"1","source_close":0,"signal":"BUY"}],self.c)
 def test_bad_load(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"x";p.write_text("bad")
   with self.assertRaises(ValueError): load_signal_rows(p)
 def test_reuse(self):
  with TemporaryDirectory() as t:
   r=Path(t);src=r/"s";src.write_text("{}");sim=simulate_portfolio(fixture(),self.c);st=validate_simulation(sim)
   store_portfolio(r/"o",src,sim,st);self.assertTrue(store_portfolio(r/"o",src,sim,st)["reused_existing_simulation"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   r=Path(t);src=r/"s";src.write_text("{}");sim=simulate_portfolio(fixture(),self.c);st=validate_simulation(sim)
   z=store_portfolio(r/"o",src,sim,st);self.assertTrue(verify_portfolio_manifest(r/"o",z["manifest"]))
 def test_tamper(self):
  with TemporaryDirectory() as t:
   r=Path(t);src=r/"s";src.write_text("{}");sim=simulate_portfolio(fixture(),self.c);st=validate_simulation(sim)
   z=store_portfolio(r/"o",src,sim,st);(r/"o/portfolio_trade_ledger.json").write_text("{}")
   with self.assertRaises(ValueError): verify_portfolio_manifest(r/"o",z["manifest"])
 def test_bad_cert(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c";p.write_text("{}")
   with self.assertRaises(ValueError): validate_signal_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/historical_portfolio_simulation_v79_76_80.py").read_text().lower()
  self.assertNotIn("submit_order(",s);self.assertNotIn("tradingclient(",s);self.assertNotIn("api_secret",s)
if __name__=="__main__":unittest.main()
