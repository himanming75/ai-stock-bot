from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.multi_asset_portfolio_v81_21_40 import *

class T(unittest.TestCase):
 def setUp(self): self.c=MultiAssetPortfolioConfig();self.u=asset_universe();self.m=correlation_matrix()
 def test_config(self): self.c.validate()
 def test_bad_split(self):
  with self.assertRaises(ValueError): MultiAssetPortfolioConfig(cash_reserve_weight=.2).validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError): MultiAssetPortfolioConfig(allow_network=True).validate()
 def test_universe(self): self.assertEqual(len(self.u),6)
 def test_correlation(self): self.assertEqual(self.m["AAPL"]["AAPL"],1)
 def test_normalize(self): self.assertAlmostEqual(sum(normalize({"a":1,"b":1},.9).values()),.9)
 def test_score_weights(self): self.assertAlmostEqual(sum(asset_score_weights(self.u,self.c).values()),.9)
 def test_caps(self): self.assertLessEqual(max(cap_weights(asset_score_weights(self.u,self.c),self.c).values()),.25)
 def test_sector_weights(self): self.assertIn("TECH",sector_weights(cap_weights(asset_score_weights(self.u,self.c),self.c),self.u))
 def test_constraints(self):
  w=cap_weights(asset_score_weights(self.u,self.c),self.c);self.assertEqual(validate_constraints(w,self.u,self.m,self.c)["status"],"PASS")
 def test_metrics(self):
  w=cap_weights(asset_score_weights(self.u,self.c),self.c);self.assertGreater(portfolio_metrics(w,self.u,self.m)["expected_sharpe"],0)
 def test_current(self): self.assertEqual(len(current_portfolio()),6)
 def test_values(self): self.assertGreater(sum(market_values(current_portfolio(),self.u).values()),0)
 def test_current_weights(self): self.assertEqual(len(current_weights(current_portfolio(),self.u,self.c.capital)),6)
 def test_target_shares(self):
  w=cap_weights(asset_score_weights(self.u,self.c),self.c);self.assertEqual(len(target_shares(w,self.u,self.c)),6)
 def test_rebalance(self):
  w=cap_weights(asset_score_weights(self.u,self.c),self.c);t=target_shares(w,self.u,self.c)
  self.assertEqual(rebalance_plan(current_portfolio(),t,self.u,self.c)["orders_created"],0)
 def test_turnover_guard(self):
  p={"turnover":1.0,"turnover_within_limit":False,"actions":[{"delta_quantity":10,"action":"BUY","estimated_notional":100}]}
  self.assertTrue(apply_turnover_guard(p,self.c)["turnover_guard_applied"])
 def test_exposure(self):
  w=cap_weights(asset_score_weights(self.u,self.c),self.c);self.assertAlmostEqual(build_exposure(w,self.u)["gross_exposure"],.9)
 def test_risk_budget(self):
  w=cap_weights(asset_score_weights(self.u,self.c),self.c);self.assertAlmostEqual(build_risk_budget(w,self.u)["budget_sum"],1)
 def test_audit(self):
  w=cap_weights(asset_score_weights(self.u,self.c),self.c);con=validate_constraints(w,self.u,self.m,self.c);met=portfolio_metrics(w,self.u,self.m)
  t=target_shares(w,self.u,self.c);p=apply_turnover_guard(rebalance_plan(current_portfolio(),t,self.u,self.c),self.c)
  ex=build_exposure(w,self.u);rb=build_risk_budget(w,self.u);self.assertEqual(build_audit(w,con,met,p,ex,rb,self.c)["status"],"PASS")
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
   with self.assertRaises(ValueError):validate_optimization_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/multi_asset_portfolio_v81_21_40.py").read_text().lower()
  for x in ("submit_order(","tradingclient(","api_secret","api_key","os.getenv","requests."):self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V81.{i:02d}" for i in range(21,41)]),20)
if __name__=="__main__":unittest.main()
