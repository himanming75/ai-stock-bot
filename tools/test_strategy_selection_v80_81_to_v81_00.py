from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.strategy_selection_v80_81_v81_00 import *

class T(unittest.TestCase):
 def setUp(self): self.c=StrategySelectionConfig();self.fixtures=market_fixture()
 def test_config(self): self.c.validate()
 def test_bad_weights(self):
  with self.assertRaises(ValueError): StrategySelectionConfig(weight_return=1).validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError): StrategySelectionConfig(allow_network=True).validate()
 def test_fixture(self): self.assertEqual(len(self.fixtures),4)
 def test_bad_series(self):
  with self.assertRaises(ValueError): validate_series([1,2])
 def test_positions(self):
  for s in ("SMA_CROSS","RSI_MEAN_REVERSION","MOMENTUM","BREAKOUT"):
   self.assertEqual(len(strategy_positions(s,self.fixtures["TREND_UP"])),10)
 def test_backtest(self):
  r=run_backtest("MOMENTUM","TREND_UP",self.fixtures["TREND_UP"],100000);self.assertEqual(r["status"],"PASS")
 def test_matrix(self):
  self.assertEqual(len(execute_matrix(["SMA_CROSS","RSI_MEAN_REVERSION","MOMENTUM","BREAKOUT"],self.fixtures,self.c)),16)
 def test_aggregate(self):
  m=execute_matrix(["SMA_CROSS","RSI_MEAN_REVERSION","MOMENTUM","BREAKOUT"],self.fixtures,self.c)
  self.assertEqual(aggregate_strategy("MOMENTUM",m,self.c)["regime_count"],4)
 def test_normalize(self):
  aggregates=[
   {"strategy_id":"A","average_return":0.0,"average_sharpe":0.0,"worst_drawdown_pct":0.1,"win_rate":0.0,"return_stability":0.0,"eligible":True},
   {"strategy_id":"B","average_return":1.0,"average_sharpe":1.0,"worst_drawdown_pct":0.0,"win_rate":1.0,"return_stability":1.0,"eligible":True},
  ]
  ranked=rank_strategies(aggregates,self.c)
  self.assertGreater(ranked[0]["selection_score"],ranked[1]["selection_score"])
 def test_rank(self):
  m=execute_matrix(["SMA_CROSS","RSI_MEAN_REVERSION","MOMENTUM","BREAKOUT"],self.fixtures,self.c)
  a=[aggregate_strategy(s,m,self.c) for s in ("SMA_CROSS","RSI_MEAN_REVERSION","MOMENTUM","BREAKOUT")]
  r=rank_strategies(a,self.c);self.assertEqual([x["rank"] for x in r],[1,2,3,4])
 def test_selection(self):
  m=execute_matrix(["SMA_CROSS","RSI_MEAN_REVERSION","MOMENTUM","BREAKOUT"],self.fixtures,self.c)
  a=[aggregate_strategy(s,m,self.c) for s in ("SMA_CROSS","RSI_MEAN_REVERSION","MOMENTUM","BREAKOUT")]
  self.assertTrue(select_champion(rank_strategies(a,self.c),self.c)["champion_strategy_id"])
 def test_leaderboard(self):
  rows=[{"rank":1,"strategy_id":"X","selection_score":1,"eligible":True,"average_return":1,"average_sharpe":1,"worst_drawdown_pct":0,"win_rate":1}]
  self.assertEqual(build_leaderboard(rows)["strategy_count"],1)
 def test_no_eligible(self):
  with self.assertRaises(ValueError): select_champion([{"eligible":False,"selection_score":-1}],self.c)
 def test_audit(self):
  matrix=[{}]*16;aggregates=[{}]*4;ranked=[{"rank":i} for i in range(1,5)]
  selection={"champion_strategy_id":"X","promotion_authorized":False,"order_submission_authorized":False}
  self.assertEqual(build_audit(matrix,aggregates,ranked,selection)["status"],"PASS")
 def test_store_reuse(self):
  with TemporaryDirectory() as t:
   out=Path(t);docs={"a":{"x":1}};store_package(out,docs);self.assertTrue(store_package(out,docs)["reused"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_package(out,{"a":{"x":1}});m=build_manifest(out,z["ledger"]);self.assertTrue(verify_manifest(out,m))
 def test_manifest_tamper(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_package(out,{"a":{"x":1}});m=build_manifest(out,z["ledger"]);(out/"packages"/z["package_id"]/"a.json").write_text("{}")
   with self.assertRaises(ValueError): verify_manifest(out,m)
 def test_bad_cert(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c";p.write_text("{}")
   with self.assertRaises(ValueError): validate_foundation_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/strategy_selection_v80_81_v81_00.py").read_text().lower()
  for x in ("submit_order(","tradingclient(","api_secret","api_key","os.getenv","requests."):self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V80.{i:02d}" for i in range(81,100)]+["V81.00"]),20)

if __name__=="__main__":unittest.main()
