import tempfile,unittest
from pathlib import Path
from ai_risk_manager.exposure import calculate_exposure
from ai_risk_manager.var import portfolio_var
from ai_risk_manager.drawdown import drawdown_risk
from ai_risk_manager.stress import stress_test
from ai_risk_manager.scoring import risk_score
from ai_risk_manager.gate import evaluate_gate
from ai_risk_manager.engine import evaluate

class Tests(unittest.TestCase):
    def test_exposure(self):
        value=calculate_exposure(
            {"allocation":{"allocations":[
                {"target_weight_pct":40},
                {"target_weight_pct":30}],
                "cash_weight_pct":30}},
            {"turnover":{"used_turnover_pct":10}},
        )
        self.assertEqual(value["gross_exposure_pct"],70)

    def test_var(self):
        value=portfolio_var(100000,2.0)
        self.assertGreater(value["var_amount"],0)

    def test_drawdown(self):
        value=drawdown_risk(
            {"risk":{"weighted_drawdown_pct":7}},
            {"maximum_weighted_drawdown_pct":15},
        )
        self.assertTrue(value["passed"])

    def test_stress(self):
        value=stress_test(
            100000,
            {"gross_exposure_pct":90},
            {"stress_scenarios":[
                {"scenario_id":"S","market_shock_pct":-10,
                 "exposure_multiplier":1.0}
            ]},
        )
        self.assertAlmostEqual(value["worst_estimated_loss_pct"],9.0)

    def test_score(self):
        value=risk_score(
            {"largest_strategy_weight_pct":40,"turnover_pct":10},
            {"var_pct":2},
            {"weighted_drawdown_pct":7},
            {"worst_estimated_loss_pct":9},
            {"maximum_risk_score":70},
        )
        self.assertTrue(value["passed"])

    def test_gate(self):
        value=evaluate_gate(
            {"largest_strategy_weight_pct":40,"cash_weight_pct":10,
             "turnover_pct":20},
            {"var_pct":2},
            {"passed":True},
            {"worst_estimated_loss_pct":10},
            {"passed":True},
            {"risk":{"passed":True},"execution_authorized":False,
             "manual_approval_required":True},
            {},
        )
        self.assertTrue(value["passed"])

    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(
                evaluate(Path(t))["state"],
                "AI_RISK_MANAGER_SOURCE_REQUIRED",
            )

    def test_safety(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(evaluate(Path(t))["order_submission_enabled"])

if __name__=="__main__":
    unittest.main()
