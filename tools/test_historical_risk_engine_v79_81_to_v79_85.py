from pathlib import Path
from tempfile import TemporaryDirectory
import json,unittest
from alpaca_market_data.historical_risk_engine_v79_81_85 import *

def portfolio(equities=(100,90,95),positions=None,market_value=0):
 return {"initial_cash":100,"final_cash":100-market_value,"final_equity":equities[-1],"positions":positions or {},
 "trades":[],"snapshots":[{"timestamp":str(i),"equity":e,"market_value":market_value,"cash":e-market_value,"open_position_count":len(positions or {})} for i,e in enumerate(equities)]}

class T(unittest.TestCase):
 def setUp(self): self.c=RiskConfig()
 def test_config(self): self.c.validate()
 def test_network(self):
  with self.assertRaises(ValueError): RiskConfig(allow_network=True).validate()
 def test_position_size(self): self.assertGreater(position_size(100000,100,self.c)["approved_quantity"],0)
 def test_position_cap(self):
  x=position_size(100000,100,RiskConfig(max_position_pct=.01)); self.assertLessEqual(x["approved_quantity"],10)
 def test_drawdown(self): self.assertAlmostEqual(drawdown_metrics(portfolio()["snapshots"])["max_drawdown_pct"],.1)
 def test_risk_pass(self): self.assertEqual(evaluate_risk(portfolio((100,100,100)),self.c)["status"],"PASS")
 def test_drawdown_fail(self): self.assertIn("MAX_DRAWDOWN",evaluate_risk(portfolio((100,50,60)),self.c)["violations"])
 def test_position_fail(self):
  p={str(i):1 for i in range(6)}; self.assertIn("MAX_OPEN_POSITIONS",evaluate_risk(portfolio((100,100),p),self.c)["violations"])
 def test_bad_portfolio(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"x"; p.write_text("{}")
   with self.assertRaises(ValueError): load_portfolio(p)
 def test_reuse(self):
  with TemporaryDirectory() as t:
   r=Path(t);src=r/"s";src.write_text("{}");res=evaluate_risk(portfolio((100,100)),self.c)
   store_risk(r/"o",src,res);self.assertTrue(store_risk(r/"o",src,res)["reused_existing_analysis"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   r=Path(t);src=r/"s";src.write_text("{}");res=evaluate_risk(portfolio((100,100)),self.c)
   z=store_risk(r/"o",src,res);self.assertTrue(verify_risk_manifest(r/"o",z["manifest"]))
 def test_tamper(self):
  with TemporaryDirectory() as t:
   r=Path(t);src=r/"s";src.write_text("{}");res=evaluate_risk(portfolio((100,100)),self.c)
   z=store_risk(r/"o",src,res);(r/"o/historical_risk_ledger.json").write_text("{}")
   with self.assertRaises(ValueError): verify_risk_manifest(r/"o",z["manifest"])
 def test_bad_cert(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c";p.write_text("{}")
   with self.assertRaises(ValueError): validate_portfolio_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/historical_risk_engine_v79_81_85.py").read_text().lower()
  self.assertNotIn("submit_order(",s);self.assertNotIn("tradingclient(",s);self.assertNotIn("api_secret",s)
if __name__=="__main__":unittest.main()
