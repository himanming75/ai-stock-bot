from pathlib import Path
from tempfile import TemporaryDirectory
import json,unittest
from alpaca_market_data.historical_performance_analytics_v79_86_90 import *

def pf():
 return {"initial_cash":100.0,"final_equity":110.0,
 "snapshots":[{"timestamp":"1","equity":100.0},{"timestamp":"2","equity":105.0},{"timestamp":"3","equity":95.0},{"timestamp":"4","equity":110.0}],
 "trades":[{"side":"SELL","realized_pnl":10.0},{"side":"SELL","realized_pnl":-5.0},{"side":"SELL","realized_pnl":0.0}]}

class T(unittest.TestCase):
 def setUp(self): self.c=PerformanceConfig(periods_per_year=4)
 def test_config(self): self.c.validate()
 def test_network(self):
  with self.assertRaises(ValueError): PerformanceConfig(allow_network=True).validate()
 def test_returns(self): self.assertAlmostEqual(return_metrics(pf(),self.c)["total_return"],.1)
 def test_drawdown(self): self.assertGreater(return_metrics(pf(),self.c)["max_drawdown_pct"],0)
 def test_ratios_finite(self):
  x=return_metrics(pf(),self.c); self.assertTrue(all(math.isfinite(float(x[k])) for k in ("sharpe_ratio","sortino_ratio","calmar_ratio")))
 def test_trade_metrics(self):
  x=trade_metrics(pf()["trades"]); self.assertEqual(x["closed_trade_count"],3); self.assertAlmostEqual(x["win_rate"],1/3)
 def test_profit_factor(self): self.assertEqual(trade_metrics(pf()["trades"])["profit_factor"],2.0)
 def test_zero_activity(self):
  x=analyze_performance({"initial_cash":100,"final_equity":100,"snapshots":[{"timestamp":"1","equity":100}],"trades":[]},self.c)
  self.assertEqual(x["return_metrics"]["total_return"],0)
 def test_bad_portfolio(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"x"; p.write_text("{}")
   with self.assertRaises(ValueError): load_portfolio(p)
 def test_reuse(self):
  with TemporaryDirectory() as t:
   r=Path(t);src=r/"s";src.write_text("{}");res=analyze_performance(pf(),self.c)
   store_performance(r/"o",src,res);self.assertTrue(store_performance(r/"o",src,res)["reused_existing_analysis"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   r=Path(t);src=r/"s";src.write_text("{}");res=analyze_performance(pf(),self.c)
   z=store_performance(r/"o",src,res);self.assertTrue(verify_performance_manifest(r/"o",z["manifest"]))
 def test_tamper(self):
  with TemporaryDirectory() as t:
   r=Path(t);src=r/"s";src.write_text("{}");res=analyze_performance(pf(),self.c)
   z=store_performance(r/"o",src,res);(r/"o/historical_performance_ledger.json").write_text("{}")
   with self.assertRaises(ValueError): verify_performance_manifest(r/"o",z["manifest"])
 def test_bad_cert(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c";p.write_text("{}")
   with self.assertRaises(ValueError): validate_portfolio_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/historical_performance_analytics_v79_86_90.py").read_text().lower()
  self.assertNotIn("submit_order(",s);self.assertNotIn("tradingclient(",s);self.assertNotIn("api_secret",s)
if __name__=="__main__":unittest.main()
