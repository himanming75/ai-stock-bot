import tempfile,unittest,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from optimization.strategy_optimization_pipeline_v77_71_75 import *
class Tests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
  self.report=self.r/"report.json";self.cert=self.r/"cert.json";self.cfg=self.r/"cfg.json"
  write_json(self.report,{"stage":"V77.66","status":"PASS","summary":{"total_return":0.01,"sharpe_ratio":0.2,
   "max_drawdown":0.03,"profit_factor":1.1}})
  write_json(self.cert,{"stage":"V77.70","status":"PASS"})
  write_json(self.cfg,{"search_space":{"fast_window":[10,20],"slow_window":[40,50],"signal_threshold":[0.005,0.015]},
   "objective_weights":{"total_return":0.25,"sharpe_ratio":0.25,"max_drawdown":0.20,"profit_factor":0.15,"stability_score":0.15},
   "safety_limits":{"minimum_trade_count":30,"minimum_sharpe_ratio":0.5,"maximum_drawdown":0.2,
   "minimum_profit_factor":1.05,"minimum_stability_score":0.5}})
 def tearDown(self):self.t.cleanup()
 def chain(self):
  o71=self.r/"o71";build_strategy_optimization_engine(self.report,self.cert,self.cfg,o71)
  o72=self.r/"o72";run_grid_search(o71/"strategy_optimization_engine_v77_71.json",o72)
  o73=self.r/"o73";rank_strategies(o72/"grid_search_results_v77_72.json",o71/"strategy_optimization_engine_v77_71.json",o73)
  o74=self.r/"o74";run_optimization_safety_gate(o73/"strategy_ranking_v77_73.json",self.cfg,o74)
  return issue_optimization_certificate(o71/"strategy_optimization_engine_verification_v77_71.json",
   o72/"grid_search_verification_v77_72.json",o73/"strategy_ranking_verification_v77_73.json",
   o74/"optimization_safety_gate_verification_v77_74.json",o73/"strategy_ranking_v77_73.json",
   o74/"optimization_safety_gate_v77_74.json",self.r/"o75")
 def test_full_chain(self):self.assertEqual(self.chain()["status"],"PASS")
 def test_grid_candidate_count(self):
  o=self.r/"o";build_strategy_optimization_engine(self.report,self.cert,self.cfg,o)
  d=run_grid_search(o/"strategy_optimization_engine_v77_71.json",self.r/"g");self.assertEqual(d["candidate_count"],8)
 def test_ranking_is_sorted(self):
  o=self.r/"o";build_strategy_optimization_engine(self.report,self.cert,self.cfg,o)
  g=run_grid_search(o/"strategy_optimization_engine_v77_71.json",self.r/"g")
  d=rank_strategies(self.r/"g/grid_search_results_v77_72.json",o/"strategy_optimization_engine_v77_71.json",self.r/"rank")
  scores=[x["composite_score"] for x in d["ranked_candidates"]];self.assertEqual(scores,sorted(scores,reverse=True))
 def test_deterministic_champion(self):
  c1=self.chain()["champion_candidate"]["candidate_id"];self.r.joinpath("o75").mkdir(exist_ok=True)
  c2=self.chain()["champion_candidate"]["candidate_id"];self.assertEqual(c1,c2)
 def test_invalid_parameter_order_filtered(self):
  cfg=load_json(self.cfg);cfg["search_space"]={"fast_window":[50],"slow_window":[40],"signal_threshold":[0.01]};write_json(self.cfg,cfg)
  o=self.r/"o";build_strategy_optimization_engine(self.report,self.cert,self.cfg,o)
  self.assertEqual(run_grid_search(o/"strategy_optimization_engine_v77_71.json",self.r/"g")["status"],"FAIL")
 def test_safety_invariants(self):self.assertEqual(self.chain()["actual_orders_submitted"],0)
 def test_poor_baseline_can_advance_only_to_walk_forward(self):
  write_json(self.report,{"stage":"V77.66","status":"PASS","summary":{"total_return":-0.20,"sharpe_ratio":-3.0,
   "max_drawdown":0.35,"profit_factor":0.20}})
  cert=self.chain()
  self.assertEqual(cert["status"],"PASS")
  self.assertEqual(cert["certification_scope"],"WALK_FORWARD_ELIGIBILITY_ONLY")
  self.assertFalse(cert["live_deployment_approved"])
 def test_gate_selects_safety_qualified_candidate(self):
  o71=self.r/"x71";build_strategy_optimization_engine(self.report,self.cert,self.cfg,o71)
  o72=self.r/"x72";run_grid_search(o71/"strategy_optimization_engine_v77_71.json",o72)
  o73=self.r/"x73";rank_strategies(o72/"grid_search_results_v77_72.json",o71/"strategy_optimization_engine_v77_71.json",o73)
  gate=run_optimization_safety_gate(o73/"strategy_ranking_v77_73.json",self.cfg,self.r/"x74")
  self.assertEqual(gate["status"],"PASS");self.assertIsNotNone(gate["selected_champion_candidate"])
if __name__=="__main__":unittest.main()
