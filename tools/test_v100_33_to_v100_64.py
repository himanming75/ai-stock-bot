import tempfile,unittest
from pathlib import Path
from risk_budget.kelly import fractional_kelly
from risk_budget.volatility import volatility_scale
from risk_budget.candidates import build_candidates
from risk_budget.allocation import allocate_risk_budgets
from risk_budget.exposure import dynamic_exposure_control
from risk_budget.heat import portfolio_heat
from risk_budget.gate import evaluate_gate
from risk_budget.engine import evaluate

class Tests(unittest.TestCase):
    def test_kelly(self):
        value=fractional_kelly(60,2,-1,0.25,0.5)
        self.assertGreater(value["applied_kelly_fraction"],0)

    def test_volatility(self):
        value=volatility_scale(2,4,0.25,1.25)
        self.assertEqual(value["applied_multiplier"],0.5)

    def test_candidates(self):
        value=build_candidates(
            {"allocation":{"allocations":[
                {"strategy_id":"A","target_weight_pct":40}
            ]}},
            {"strategies":[{"strategy_id":"A","win_rate_pct":55}]},
        )
        self.assertEqual(value[0]["strategy_id"],"A")

    def test_allocate(self):
        candidates=[
            {
                "strategy_id":"A","target_weight_pct":50,
                "observed_volatility_pct":2,
                "win_rate_pct":60,"average_win_pct":2,
                "average_loss_pct":-1,"risk_quality_score":80,
            },
            {
                "strategy_id":"B","target_weight_pct":40,
                "observed_volatility_pct":3,
                "win_rate_pct":55,"average_win_pct":1.5,
                "average_loss_pct":-1,"risk_quality_score":70,
            },
        ]
        value=allocate_risk_budgets(
            candidates,
            {"risk_score":{"risk_score":50}},
            {
                "total_risk_budget_pct":10,
                "maximum_strategy_risk_budget_pct":6,
                "minimum_strategy_risk_budget_pct":0.25,
                "target_strategy_volatility_pct":2,
                "kelly_fraction":0.25,
                "maximum_kelly_fraction":0.5,
                "minimum_exposure_multiplier":0.25,
                "maximum_exposure_multiplier":1.25,
            },
        )
        self.assertLessEqual(value["used_risk_budget_pct"],10)

    def test_exposure(self):
        value=dynamic_exposure_control(
            {"used_risk_budget_pct":8,"total_risk_budget_pct":10},
            {},
            {
                "exposure":{"gross_exposure_pct":90},
                "risk_score":{"risk_score":50},
                "stress":{"worst_estimated_loss_pct":10},
            },
            {"maximum_gross_exposure_pct":100,
             "minimum_gross_exposure_pct":20},
        )
        self.assertGreater(value["target_gross_exposure_pct"],0)

    def test_heat(self):
        value=portfolio_heat(
            [{"risk_budget_pct":4},{"risk_budget_pct":3}],
            {"final_exposure_multiplier":0.5},
        )
        self.assertEqual(value["portfolio_heat_pct"],3.5)

    def test_gate(self):
        value=evaluate_gate(
            {
                "allocations":[{"risk_budget_pct":4}],
                "used_risk_budget_pct":4,
                "total_risk_budget_pct":10,
            },
            {
                "target_gross_exposure_pct":50,
                "final_exposure_multiplier":0.5,
            },
            {"portfolio_heat_pct":2},
            {
                "maximum_strategy_risk_budget_pct":5,
                "maximum_portfolio_heat_pct":10,
                "maximum_gross_exposure_pct":100,
            },
        )
        self.assertTrue(value["passed"])

    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(
                evaluate(Path(t))["state"],
                "RISK_BUDGET_SOURCE_REQUIRED",
            )

    def test_safety(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(evaluate(Path(t))["order_submission_enabled"])

if __name__=="__main__":
    unittest.main()
