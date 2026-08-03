import tempfile, unittest
from pathlib import Path
from meta_strategy_engine.scoring import normalized_score, strategy_meta_score
from meta_strategy_engine.allocation import allocate
from meta_strategy_engine.decision import final_position_multiplier, paper_decision
from meta_strategy_engine.engine import evaluate

class Tests(unittest.TestCase):
    def test_normalized_score(self):
        self.assertEqual(normalized_score(5,0,10),0.5)
    def test_meta_score(self):
        row={"strategy_id":"MOMENTUM_10","base_strategy":"MOMENTUM","full_result":{"total_return_pct":10,"sharpe_ratio":1,"maximum_drawdown_pct":5,"win_rate_pct":60}}
        result=strategy_meta_score(row,["MOMENTUM"],"MOMENTUM_10",True,{
            "return_score":.2,"sharpe_score":.2,"drawdown_score":.2,
            "win_rate_score":.1,"regime_score":.1,"stability_score":.1,"risk_score":.1})
        self.assertGreater(result["meta_score"],0)
    def test_allocate(self):
        ranked=[{"strategy_id":"A","base_strategy":"A","meta_score":2,"meta_rank":1},{"strategy_id":"B","base_strategy":"B","meta_score":1,"meta_rank":2}]
        self.assertAlmostEqual(sum(x["weight_pct"] for x in allocate(ranked,2,70)),100,places=2)
    def test_multiplier(self):
        self.assertLess(final_position_multiplier(.5,True,60,True),.5)
    def test_decision_normal(self):
        self.assertEqual(paper_decision([{"weight_pct":100}],.8,True,True),"PAPER_TRADE_NORMAL_EXPOSURE")
    def test_decision_review(self):
        self.assertEqual(paper_decision([{"weight_pct":100}],.8,False,False),"REVIEW_REQUIRED")
    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["state"],"META_STRATEGY_SOURCE_REQUIRED")
    def test_safety(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(evaluate(Path(t))["order_submission_enabled"])

if __name__=="__main__": unittest.main()
