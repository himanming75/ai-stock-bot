import json,tempfile,unittest
from pathlib import Path
from walk_forward.walk_forward_pipeline_v77_76_80 import *

class Tests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
  self.cert=self.r/"cert.json";self.cfg=self.r/"cfg.json"
  write_json(self.cert,{"stage":"V77.75","status":"PASS","certification_scope":"WALK_FORWARD_ELIGIBILITY_ONLY",
   "champion_candidate":{"candidate_id":"abc123","parameters":{"fast_window":20,"slow_window":50,"signal_threshold":0.015},
    "metrics":{"total_return":0.08,"sharpe_ratio":1.4,"max_drawdown":0.12,"profit_factor":1.5,"trade_count":80,"stability_score":0.8}}})
  write_json(self.cfg,{"walk_forward":{"window_mode":"rolling","fold_count":6,"train_periods":252,"test_periods":63,"step_periods":63},
   "walk_forward_safety_limits":{"minimum_positive_fold_ratio":0.6,"minimum_average_sharpe_ratio":0.25,
    "minimum_average_profit_factor":1.0,"maximum_average_drawdown":0.5,"maximum_return_variance":0.005,
    "minimum_average_stability_score":0.45,"minimum_worst_fold_sharpe_ratio":-1.0}})
 def tearDown(self):self.t.cleanup()
 def chain(self):
  o76=self.r/"o76";a=build_walk_forward_engine(self.cert,self.cfg,o76)
  o77=self.r/"o77";b=build_rolling_windows(o76/"walk_forward_engine_v77_76.json",o77)
  o78=self.r/"o78";c=analyze_out_of_sample(o76/"walk_forward_engine_v77_76.json",o77/"rolling_windows_v77_77.json",o78)
  o79=self.r/"o79";d=run_walk_forward_safety_gate(o78/"out_of_sample_analysis_v77_78.json",self.cfg,o79)
  o80=self.r/"o80";e=issue_walk_forward_certificate(
   o76/"walk_forward_engine_verification_v77_76.json",o77/"rolling_windows_verification_v77_77.json",
   o78/"out_of_sample_analysis_verification_v77_78.json",o79/"walk_forward_safety_gate_verification_v77_79.json",
   o76/"walk_forward_engine_v77_76.json",o78/"out_of_sample_analysis_v77_78.json",o80)
  return a,b,c,d,e
 def test_full_chain(self):self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))
 def test_fold_count(self):self.assertEqual(self.chain()[1]["fold_count"],6)
 def test_deterministic_analysis(self):self.assertEqual(self.chain()[2]["summary"],self.chain()[2]["summary"])
 def test_windows_do_not_overlap_train_test(self):
  for f in self.chain()[1]["folds"]:self.assertEqual(f["train"]["end_period_exclusive"],f["test"]["start_period"])
 def test_certificate_scope(self):
  cert=self.chain()[4];self.assertEqual(cert["certification_scope"],"ROBUSTNESS_ELIGIBILITY_ONLY");self.assertFalse(cert["live_deployment_approved"])
 def test_safety_invariants(self):
  for x in self.chain():self.assertEqual(x["actual_orders_submitted"],0);self.assertFalse(x["network_allowed"])
 def test_invalid_certificate_rejected(self):
  write_json(self.cert,{"stage":"V77.75","status":"FAIL"});self.assertEqual(build_walk_forward_engine(self.cert,self.cfg,self.r/"bad")["status"],"FAIL")

 def test_negative_candidate_uses_retention_rule(self):
  write_json(self.cert,{"stage":"V77.75","status":"PASS","certification_scope":"WALK_FORWARD_ELIGIBILITY_ONLY",
   "champion_candidate":{"candidate_id":"negative","parameters":{"fast_window":20,"slow_window":50,"signal_threshold":0.015},
    "metrics":{"total_return":-0.05,"sharpe_ratio":1.4,"max_drawdown":0.12,"profit_factor":1.5,"trade_count":80,"stability_score":0.8}}})
  gate=self.chain()[3]
  self.assertEqual(gate["status"],"PASS")
  self.assertFalse(gate["candidate_positive_return"])

 def test_positive_candidate_keeps_positive_fold_rule(self):
  p=self.r/"positive_weak.json";write_json(p,{"stage":"V77.78","status":"PASS","summary":{
   "candidate_expected_return":0.1,"return_retention_floor":0.04,"fold_retention_ratio":1.0,
   "average_total_return":0.05,"positive_fold_ratio":0.1,"average_sharpe_ratio":1.0,
   "average_profit_factor":1.2,"average_max_drawdown":0.2,"return_variance":0.001,
   "average_stability_score":0.7,"worst_fold_sharpe_ratio":0.0}})
  gate=run_walk_forward_safety_gate(p,self.cfg,self.r/"positive_gate")
  self.assertEqual(gate["status"],"FAIL")
  self.assertIn("positive_fold_ratio_when_candidate_positive",gate["failed_checks"])

 def test_gate_blocks_weak_analysis(self):
  p=self.r/"weak.json";write_json(p,{"stage":"V77.78","status":"PASS","summary":{"positive_fold_ratio":0.0,
   "average_sharpe_ratio":-2,"average_profit_factor":0.2,"average_max_drawdown":0.9,"return_variance":1,
   "average_stability_score":0.1,"worst_fold_sharpe_ratio":-5}})
  self.assertEqual(run_walk_forward_safety_gate(p,self.cfg,self.r/"gate")["status"],"FAIL")
if __name__=="__main__":unittest.main()
