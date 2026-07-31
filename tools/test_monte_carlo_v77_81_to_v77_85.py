import tempfile,unittest
from pathlib import Path
from monte_carlo.monte_carlo_pipeline_v77_81_85 import *
import monte_carlo.monte_carlo_pipeline_v77_81_85 as mcmod

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
        self.cert=self.r/"cert.json";self.cfg=self.r/"cfg.json"
        write_json(self.cert,{"stage":"V77.80","status":"PASS","certification_scope":"ROBUSTNESS_ELIGIBILITY_ONLY",
          "champion_candidate":{"candidate_id":"abc","parameters":{"fast_window":20,"slow_window":50,"signal_threshold":0.015},
          "metrics":{"total_return":0.08,"sharpe_ratio":1.4,"max_drawdown":0.12,
                     "profit_factor":1.5,"trade_count":80,"stability_score":0.8}},
          "out_of_sample_summary":{"average_total_return":0.04}})
        write_json(self.cfg,{"monte_carlo":{"simulation_count":200,"trade_sequence_length":60,"base_seed":123,
          "slippage_bps_range":[0,5],"commission_bps_range":[0,2],"partial_fill_ratio_range":[0.8,1.0],
          "tail_shock_scenario_probability":0.01,"tail_shock_return_range":[-0.05,-0.02],
          "bankruptcy_survival_equity_floor":0.25,"capital_preservation_equity_floor":0.70},
          "monte_carlo_safety_limits":{"minimum_bankruptcy_survival_rate":0.50,"maximum_drawdown_p95":0.95,
          "maximum_catastrophic_drawdown_probability":1.0,"minimum_terminal_equity_p05":0.10,
          "minimum_return_retention_rate":0.0,"minimum_hard_sharpe_p05":-20.0,
          "maximum_sharpe_tail_spread":20.0,"maximum_loss_probability":1.0}})
    def tearDown(self):self.t.cleanup()
    def chain(self):
        o81=self.r/"o81";a=build_monte_carlo_engine(self.cert,self.cfg,o81)
        o82=self.r/"o82";b=run_randomized_execution_simulator(o81/"monte_carlo_engine_v77_81.json",o82)
        o83=self.r/"o83";c=analyze_robustness_distribution(o82/"randomized_execution_simulation_v77_82.json",o83)
        o84=self.r/"o84";d=run_monte_carlo_safety_gate(o83/"robustness_distribution_v77_83.json",self.cfg,o84)
        o85=self.r/"o85";e=issue_monte_carlo_certificate(
          o81/"monte_carlo_engine_verification_v77_81.json",
          o82/"randomized_execution_simulation_verification_v77_82.json",
          o83/"robustness_distribution_verification_v77_83.json",
          o84/"monte_carlo_safety_gate_verification_v77_84.json",
          o81/"monte_carlo_engine_v77_81.json",
          o83/"robustness_distribution_v77_83.json",o85)
        return a,b,c,d,e
    def test_full_chain(self):self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))
    def test_simulation_count(self):self.assertEqual(self.chain()[1]["simulation_count"],200)
    def test_deterministic_distribution(self):
        self.assertEqual(self.chain()[2]["summary"],self.chain()[2]["summary"])
    def test_certificate_scope(self):
        cert=self.chain()[4];self.assertEqual(cert["certification_scope"],"STRESS_TEST_ELIGIBILITY_ONLY")
        self.assertFalse(cert["live_deployment_approved"])
    def test_safety_invariants(self):
        for x in self.chain():
            self.assertEqual(x["actual_orders_submitted"],0)
            self.assertFalse(x["network_allowed"])
    def test_invalid_certificate_rejected(self):
        write_json(self.cert,{"stage":"V77.80","status":"FAIL"})
        self.assertEqual(build_monte_carlo_engine(self.cert,self.cfg,self.r/"bad")["status"],"FAIL")

    def test_tail_shock_is_scenario_level(self):
        sim=self.chain()[1]
        shock_count=sum(x["tail_shock_applied"] for x in sim["scenarios"])
        self.assertLess(shock_count,sim["simulation_count"])
        self.assertEqual(sim["shock_model"],"AT_MOST_ONE_TAIL_SHOCK_PER_SCENARIO")

    def test_non_positive_median_does_not_certify_profitability(self):
        p=self.r/"negative_dist.json"
        write_json(p,{"stage":"V77.83","status":"PASS","summary":{
          "survival_rate":0.99,"capital_preservation_rate":0.20,
          "drawdown_p95":0.40,"catastrophic_drawdown_probability":0.05,
          "terminal_equity_p05":0.60,"return_retention_rate":0.95,
          "sharpe_p05":-2.0,"sharpe_tail_spread":2.0,
          "loss_probability":1.0,"return_p50":-0.05}})
        gate=run_monte_carlo_safety_gate(p,self.cfg,self.r/"negative_gate")
        self.assertEqual(gate["status"],"PASS")
        self.assertFalse(gate["median_return_positive"])
        self.assertFalse(gate["profitability_certified"])


    def test_survival_and_capital_preservation_are_separate(self):
        sim=self.chain()[1]
        self.assertTrue(all("survived" in x and "capital_preserved" in x for x in sim["scenarios"]))
        dist=self.chain()[2]["summary"]
        self.assertIn("survival_rate",dist)
        self.assertIn("capital_preservation_rate",dist)

    def test_tail_sharpe_uses_hard_and_relative_checks(self):
        p=self.r/"tail.json"
        write_json(p,{"stage":"V77.83","status":"PASS","summary":{
          "survival_rate":0.99,"capital_preservation_rate":0.1,
          "drawdown_p95":0.4,"catastrophic_drawdown_probability":0.05,
          "terminal_equity_p05":0.5,"return_retention_rate":0.99,
          "sharpe_p05":-3.0,"sharpe_tail_spread":2.0,
          "loss_probability":1.0,"return_p50":-0.1}})
        gate=run_monte_carlo_safety_gate(p,self.cfg,self.r/"tail_gate")
        self.assertEqual(gate["status"],"PASS")
        self.assertFalse(gate["capital_preservation_certified"])

    def test_weak_distribution_blocked(self):
        p=self.r/"weak.json";write_json(p,{"stage":"V77.83","status":"PASS","summary":{
          "survival_rate":0.1,"drawdown_p95":0.9,"catastrophic_drawdown_probability":0.8,
          "terminal_equity_p05":0.1,"return_retention_rate":0.1,
          "sharpe_p05":-20,"sharpe_tail_spread":30,
          "capital_preservation_rate":0.0,"loss_probability":1.0,"return_p50":0.1}})
        self.assertEqual(run_monte_carlo_safety_gate(p,self.cfg,self.r/"gate")["status"],"FAIL")
    def test_percentile_monotonic(self):
        xs=[1,2,3,4,5]
        self.assertLessEqual(mcmod._percentile(xs,0.05),mcmod._percentile(xs,0.50))
        self.assertLessEqual(mcmod._percentile(xs,0.50),mcmod._percentile(xs,0.95))
if __name__=="__main__":unittest.main()
