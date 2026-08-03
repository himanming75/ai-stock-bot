import unittest
from v89_portfolio.scoring import strategy_score, rank_strategies
from v89_portfolio.sizing import equal_weight, score_weight, inverse_drawdown_weight, kelly_fraction, capped_weights
from v89_portfolio.risk import evaluate_portfolio_risk
from v89_portfolio.optimizer import optimize

def rows():
    return [
        {"strategy":"EMA_CROSS","total_return_pct":12,"maximum_drawdown_pct":5,"sharpe_ratio":1.2,"win_rate_pct":60,"profit_factor":1.5,"gate":{"approved":True}},
        {"strategy":"RSI","total_return_pct":8,"maximum_drawdown_pct":4,"sharpe_ratio":0.8,"win_rate_pct":55,"profit_factor":1.2,"gate":{"approved":True}},
        {"strategy":"MACD","total_return_pct":5,"maximum_drawdown_pct":12,"sharpe_ratio":0.3,"win_rate_pct":45,"profit_factor":0.9,"gate":{"approved":False}},
    ]

class Tests(unittest.TestCase):
    def test_score(self): self.assertGreater(strategy_score(rows()[0]), strategy_score(rows()[2]))
    def test_rank(self): self.assertEqual(rank_strategies(rows())[0]["portfolio_rank"],1)
    def test_equal_weight(self): self.assertAlmostEqual(sum(equal_weight(["A","B"]).values()),1)
    def test_score_weight(self): self.assertAlmostEqual(sum(score_weight(rank_strategies(rows())).values()),1)
    def test_inverse_weight(self): self.assertAlmostEqual(sum(inverse_drawdown_weight(rows()).values()),1)
    def test_kelly(self): self.assertGreaterEqual(kelly_fraction(60,1.5),0)
    def test_cap(self): self.assertAlmostEqual(sum(capped_weights({"A":.8,"B":.1,"C":.1},.5).values()),1)
    def test_risk(self):
        result=evaluate_portfolio_risk({"A":.5,"B":.5},rows(),{"maximum_single_allocation_pct":60,"minimum_approved_strategies":1})
        self.assertIn("passed",result)
    def test_optimize(self):
        result=optimize({"strategy_rankings":rows()},{"allocation_mode":"SCORE_WEIGHT","maximum_single_allocation_pct":60})
        self.assertGreaterEqual(result["eligible_strategy_count"],1)
    def test_empty_source_is_reviewable(self):
        result=optimize({"strategy_rankings":[]},{})
        self.assertEqual(result["eligible_strategy_count"],0)
        self.assertEqual(result["allocations"],[])

    def test_safety(self):
        result=optimize({"strategy_rankings":rows()},{})
        self.assertFalse(result["order_submission_enabled"])

if __name__=="__main__":
    unittest.main()
