import tempfile,unittest
from pathlib import Path
from risk_stress.risk_stress_pipeline_v77_86_90 import *
import risk_stress.risk_stress_pipeline_v77_86_90 as rsmod

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name)
        self.cert=self.r/"cert.json";self.cfg=self.r/"cfg.json"
        write_json(self.cert,{"stage":"V77.85","status":"PASS","certification_scope":"STRESS_TEST_ELIGIBILITY_ONLY",
          "champion_candidate":{"candidate_id":"abc","parameters":{"fast_window":20,"slow_window":50,"signal_threshold":0.015},
          "metrics":{"total_return":0.08,"sharpe_ratio":1.4,"max_drawdown":0.12,
                     "profit_factor":1.5,"trade_count":80,"stability_score":0.8}},
          "robustness_summary":{"survival_rate":0.95}})
        write_json(self.cfg,{"stress_scenarios":[
          {"scenario_id":"A","scenario_class":"DIAGNOSTIC_EXTREME","gate_required":False,"expected_action":"HALT_NEW_ORDERS","name":"Flash","severity":1.5,"gap_return":-0.1,"volatility_multiplier":3,"spread_multiplier":4,"liquidity_ratio":0.4,"halt_probability":0.2},
          {"scenario_id":"B","scenario_class":"OPERATIONAL_STRESS","gate_required":True,"expected_action":"CONTINUE_WITH_RISK_LIMITS","name":"Bear","severity":1.1,"gap_return":-0.05,"volatility_multiplier":2,"spread_multiplier":2,"liquidity_ratio":0.7,"halt_probability":0.1},
          {"scenario_id":"C","scenario_class":"OPERATIONAL_STRESS","gate_required":True,"expected_action":"CONTINUE_WITH_RISK_LIMITS","name":"Sideways","severity":0.8,"gap_return":-0.02,"volatility_multiplier":1.5,"spread_multiplier":1.5,"liquidity_ratio":0.9,"halt_probability":0},
          {"scenario_id":"D","scenario_class":"OPERATIONAL_STRESS","gate_required":True,"expected_action":"CONTINUE_WITH_RISK_LIMITS","name":"Liquidity","severity":1.4,"gap_return":-0.08,"volatility_multiplier":2.5,"spread_multiplier":5,"liquidity_ratio":0.25,"halt_probability":0.2},
          {"scenario_id":"E","scenario_class":"OPERATIONAL_STRESS","gate_required":True,"expected_action":"CONTINUE_WITH_RISK_LIMITS","name":"Recovery","severity":0.5,"gap_return":-0.01,"volatility_multiplier":1.2,"spread_multiplier":1.2,"liquidity_ratio":1.0,"halt_probability":0}
        ],"risk_stress_safety_limits":{"maximum_operational_worst_drawdown":0.99,
          "minimum_operational_position_survival_rate":0.0,"minimum_operational_cash_survival_ratio":0.0,
          "maximum_operational_critical_liquidity_failure_probability":1.0,"maximum_operational_critical_gap_failure_probability":1.0,
          "minimum_operational_fill_probability":0.0,"minimum_operational_worst_stressed_sharpe":-20,
          "diagnostic_minimum_cash_survival_ratio":-1.0,"diagnostic_total_ruin_drawdown":1.1}})
    def tearDown(self):self.t.cleanup()
    def chain(self):
        o86=self.r/"o86";a=build_risk_stress_engine(self.cert,self.cfg,o86)
        o87=self.r/"o87";b=run_market_regime_shock_simulator(o86/"risk_stress_engine_v77_86.json",o87)
        o88=self.r/"o88";c=analyze_liquidity_gap_risk(o87/"market_regime_shock_results_v77_87.json",o88)
        o89=self.r/"o89";d=run_risk_stress_safety_gate(o88/"liquidity_gap_risk_analysis_v77_88.json",self.cfg,o89)
        o90=self.r/"o90";e=issue_risk_stress_certificate(
          o86/"risk_stress_engine_verification_v77_86.json",
          o87/"market_regime_shock_verification_v77_87.json",
          o88/"liquidity_gap_risk_analysis_verification_v77_88.json",
          o89/"risk_stress_safety_gate_verification_v77_89.json",
          o86/"risk_stress_engine_v77_86.json",
          o88/"liquidity_gap_risk_analysis_v77_88.json",o90)
        return a,b,c,d,e
    def test_full_chain(self):self.assertTrue(all(x["status"]=="PASS" for x in self.chain()))
    def test_scenario_count(self):self.assertEqual(self.chain()[1]["scenario_count"],5)
    def test_certificate_scope(self):
        cert=self.chain()[4];self.assertEqual(cert["certification_scope"],"LIVE_READINESS_AUDIT_ELIGIBILITY_ONLY")
        self.assertFalse(cert["live_deployment_approved"])
    def test_safety_invariants(self):
        for x in self.chain():
            self.assertEqual(x["actual_orders_submitted"],0)
            self.assertFalse(x["network_allowed"])
    def test_invalid_certificate_rejected(self):
        write_json(self.cert,{"stage":"V77.85","status":"FAIL"})
        self.assertEqual(build_risk_stress_engine(self.cert,self.cfg,self.r/"bad")["status"],"FAIL")

    def test_operational_and_diagnostic_scenarios_are_separate(self):
        analysis=self.chain()[2]
        self.assertGreaterEqual(analysis["operational_summary"]["scenario_count"],3)
        self.assertGreaterEqual(analysis["diagnostic_extreme_summary"]["scenario_count"],1)

    def test_diagnostic_scenarios_require_emergency_action(self):
        analysis=self.chain()[2]
        self.assertTrue(analysis["emergency_action_summary"]["all_diagnostic_scenarios_have_emergency_action"])


    def test_gap_failure_uses_incremental_loss_not_baseline_return(self):
        results=[
          {"stressed_return":-0.80,"incremental_stress_loss":0.10,"stressed_drawdown":0.3,
           "fill_probability":0.5,"cash_survival_ratio":0.7,"position_survived":True,
           "stressed_sharpe":-1.0,"critical_fill_floor":0.10,"critical_incremental_loss":0.35},
          {"stressed_return":-0.90,"incremental_stress_loss":0.20,"stressed_drawdown":0.4,
           "fill_probability":0.4,"cash_survival_ratio":0.6,"position_survived":True,
           "stressed_sharpe":-2.0,"critical_fill_floor":0.10,"critical_incremental_loss":0.35},
        ]
        summary=rsmod._aggregate_results(results)
        self.assertEqual(summary["gap_failure_probability"],0.0)

    def test_liquidity_failure_means_effectively_unfillable(self):
        results=[
          {"stressed_return":-0.1,"incremental_stress_loss":0.1,"stressed_drawdown":0.2,
           "fill_probability":0.20,"cash_survival_ratio":0.8,"position_survived":True,
           "stressed_sharpe":-1.0,"critical_fill_floor":0.10,"critical_incremental_loss":0.35},
          {"stressed_return":-0.2,"incremental_stress_loss":0.2,"stressed_drawdown":0.3,
           "fill_probability":0.05,"cash_survival_ratio":0.7,"position_survived":True,
           "stressed_sharpe":-2.0,"critical_fill_floor":0.10,"critical_incremental_loss":0.35},
        ]
        summary=rsmod._aggregate_results(results)
        self.assertEqual(summary["liquidity_failure_probability"],0.5)

    def test_weak_analysis_blocked(self):
        p=self.r/"weak.json";write_json(p,{"stage":"V77.88","status":"PASS",
          "operational_summary":{"worst_stressed_drawdown":0.99,"position_survival_rate":0.0,
          "minimum_cash_survival_ratio":0.0,"liquidity_failure_probability":1.0,
          "gap_failure_probability":1.0,"minimum_fill_probability":0.0,"worst_stressed_sharpe":-99},
          "diagnostic_extreme_summary":{"minimum_cash_survival_ratio":0.0,"worst_stressed_drawdown":1.0},
          "emergency_action_summary":{"all_diagnostic_scenarios_have_emergency_action":False}})
        strict=self.r/"strict.json";write_json(strict,{"risk_stress_safety_limits":{
          "maximum_operational_worst_drawdown":0.8,"minimum_operational_position_survival_rate":0.5,
          "minimum_operational_cash_survival_ratio":0.1,"maximum_operational_critical_liquidity_failure_probability":0.5,
          "maximum_operational_critical_gap_failure_probability":0.5,"minimum_operational_fill_probability":0.05,
          "minimum_operational_worst_stressed_sharpe":-8,
          "diagnostic_minimum_cash_survival_ratio":0.0,"diagnostic_total_ruin_drawdown":1.0}})
        self.assertEqual(run_risk_stress_safety_gate(p,strict,self.r/"gate")["status"],"FAIL")
    def test_deterministic_scenario_result(self):
        a=self.chain()[1]["results"];b=self.chain()[1]["results"];self.assertEqual(a,b)
    def test_fill_probability_bounded(self):
        for x in self.chain()[1]["results"]:
            self.assertGreaterEqual(x["fill_probability"],0.0);self.assertLessEqual(x["fill_probability"],1.0)
if __name__=="__main__":unittest.main()
