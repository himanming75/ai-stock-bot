import tempfile,unittest
from pathlib import Path
from ai_portfolio_manager.candidates import build_candidates
from ai_portfolio_manager.scoring import score_candidate,rank_candidates
from ai_portfolio_manager.allocation import allocate
from ai_portfolio_manager.risk import evaluate_risk
from ai_portfolio_manager.engine import evaluate

class Tests(unittest.TestCase):
    def test_candidates(self):
        rows=build_candidates([{
            "state":"COMPLETED","strategy_id":"A",
            "regression_score":5,"adjusted_return_pct":10,
            "adjusted_drawdown_pct":3,
            "regression_gate":{"passed":True},
        }])
        self.assertEqual(rows[0]["strategy_id"],"A")

    def test_score(self):
        self.assertGreater(score_candidate({
            "average_return_pct":10,
            "average_regression_score":5,
            "worst_drawdown_pct":2,
            "pass_rate_pct":100,
            "all_scenarios_passed":True,
        },{}),0)

    def test_rank(self):
        rows=rank_candidates([
            {"strategy_id":"A","average_return_pct":10,"average_regression_score":5,"worst_drawdown_pct":2,"pass_rate_pct":100,"all_scenarios_passed":True},
            {"strategy_id":"B","average_return_pct":1,"average_regression_score":0,"worst_drawdown_pct":5,"pass_rate_pct":50,"all_scenarios_passed":False},
        ],{})
        self.assertEqual(rows[0]["strategy_id"],"A")

    def test_allocate(self):
        rows=[
            {"strategy_id":"A","portfolio_score":10},
            {"strategy_id":"B","portfolio_score":5},
        ]
        value=allocate(rows,{
            "minimum_cash_pct":10,
            "maximum_strategy_weight_pct":60,
            "minimum_strategy_weight_pct":5,
        })
        self.assertEqual(value["allocated_strategy_count"],2)
        self.assertAlmostEqual(
            sum(x["target_weight_pct"] for x in value["allocations"])+value["cash_weight_pct"],
            100.0,places=3
        )

    def test_single_strategy_cap_leaves_cash(self):
        value=allocate(
            [{"strategy_id":"A","portfolio_score":10}],
            {
                "minimum_cash_pct":10,
                "maximum_strategy_weight_pct":45,
                "minimum_strategy_weight_pct":5,
            },
        )
        self.assertEqual(
            value["allocations"][0]["target_weight_pct"],45
        )
        self.assertEqual(value["cash_weight_pct"],55)

    def test_risk(self):
        allocation={
            "allocations":[
                {"strategy_id":"A","target_weight_pct":45},
                {"strategy_id":"B","target_weight_pct":45},
            ],
            "cash_weight_pct":10,
        }
        rankings=[
            {"strategy_id":"A","worst_drawdown_pct":5},
            {"strategy_id":"B","worst_drawdown_pct":6},
        ]
        self.assertTrue(evaluate_risk(allocation,rankings,{
            "minimum_strategy_count":2,
            "maximum_strategy_weight_pct":50,
            "minimum_cash_pct":10,
            "maximum_weighted_drawdown_pct":15,
        })["passed"])

    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(
                evaluate(Path(t))["state"],
                "AI_PORTFOLIO_MANAGER_SOURCE_REQUIRED",
            )

    def test_safety(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(evaluate(Path(t))["order_submission_enabled"])

if __name__=="__main__": unittest.main()
