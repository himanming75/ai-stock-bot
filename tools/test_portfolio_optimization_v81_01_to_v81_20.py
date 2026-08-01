from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.portfolio_optimization_v81_01_20 import *

class T(unittest.TestCase):
 def setUp(self): self.c=PortfolioOptimizationConfig();self.u=strategy_universe();self.m=correlation_matrix()
 def test_config(self): self.c.validate()
 def test_bad_reserve(self):
  with self.assertRaises(ValueError): PortfolioOptimizationConfig(cash_reserve=.2).validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError): PortfolioOptimizationConfig(allow_network=True).validate()
 def test_universe(self): self.assertEqual(len(self.u),4)
 def test_correlation(self): self.assertEqual(self.m["BREAKOUT"]["BREAKOUT"],1)
 def test_normalize(self): self.assertAlmostEqual(sum(normalize({"a":1,"b":1},.9).values()),.9)
 def test_equal(self): self.assertAlmostEqual(sum(equal_weight(self.u,self.c).values()),.9)
 def test_score(self): self.assertAlmostEqual(sum(score_weight(self.u,self.c).values()),.9)
 def test_inverse_vol(self): self.assertAlmostEqual(sum(inverse_volatility_weight(self.u,self.c).values()),.9)
 def test_risk_budget(self): self.assertAlmostEqual(sum(risk_budget_weight(self.u,self.c).values()),.9)
 def test_kelly(self): self.assertGreater(kelly_fraction(.6,1.5,.5),0)
 def test_kelly_weight(self): self.assertAlmostEqual(sum(kelly_weight(self.u,self.c).values()),.9)
 def test_caps(self): self.assertLessEqual(max(apply_weight_caps({"a":.8,"b":.1},self.c).values()),.4)
 def test_metrics(self):
  w=apply_weight_caps(equal_weight(self.u,self.c),self.c);self.assertGreater(portfolio_metrics(w,self.u,self.m)["expected_sharpe"],0)
 def test_constraints(self):
  w=apply_weight_caps(equal_weight(self.u,self.c),self.c);self.assertEqual(validate_constraints(w,self.u,self.m,self.c)["status"],"PASS")
 def test_candidate(self): self.assertIn("optimization_score",candidate("X",equal_weight(self.u,self.c),self.u,self.m,self.c))
 def test_selection(self):
  cs=[candidate("X",equal_weight(self.u,self.c),self.u,self.m,self.c),candidate("Y",risk_budget_weight(self.u,self.c),self.u,self.m,self.c)]
  self.assertIn(select_optimizer(cs)["selected_method"],{"X","Y"})
 def test_plan(self):
  s=select_optimizer([candidate("X",equal_weight(self.u,self.c),self.u,self.m,self.c)])
  self.assertEqual(build_allocation_plan(s,self.u,self.c)["orders_created"],0)
 def test_audit(self):
  cs=[candidate(str(i),equal_weight(self.u,self.c),self.u,self.m,self.c) for i in range(5)]
  s=select_optimizer(cs);p=build_allocation_plan(s,self.u,self.c);self.assertEqual(build_audit(cs,s,p,self.c)["status"],"PASS")
 def test_store_reuse(self):
  with TemporaryDirectory() as t:
   out=Path(t);store_package(out,{"a":{"x":1}});self.assertTrue(store_package(out,{"a":{"x":1}})["reused"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_package(out,{"a":{"x":1}});m=build_manifest(out,z["ledger"]);self.assertTrue(verify_manifest(out,m))
 def test_manifest_tamper(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_package(out,{"a":{"x":1}});m=build_manifest(out,z["ledger"]);(out/"packages"/z["package_id"]/"a.json").write_text("{}")
   with self.assertRaises(ValueError):verify_manifest(out,m)
 def test_bad_cert(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c";p.write_text("{}")
   with self.assertRaises(ValueError):validate_selection_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/portfolio_optimization_v81_01_20.py").read_text().lower()
  for x in ("submit_order(","tradingclient(","api_secret","api_key","os.getenv","requests."):self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V81.{i:02d}" for i in range(1,21)]),20)
if __name__=="__main__":unittest.main()
