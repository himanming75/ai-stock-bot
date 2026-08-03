import tempfile, unittest
from pathlib import Path
from ai_explainability_pro.features import derive_features
from ai_explainability_pro.reasons import selection_reasons, risk_factors
from ai_explainability_pro.confidence import confidence_score
from ai_explainability_pro.narrative import strategy_description, build_summary
from ai_explainability_pro.engine import explain

def candidate():
    return {
        "strategy_id":"MOMENTUM_10",
        "base_strategy":"MOMENTUM",
        "parameters":{"period":5},
        "optimization_score":42,
        "full_result":{
            "total_return_pct":15,
            "maximum_drawdown_pct":8,
            "sharpe_ratio":1.2,
            "profit_factor":1.8,
            "win_rate_pct":60,
            "total_trades":8,
        },
        "walk_forward":{
            "positive_window_pct":75,
            "average_return_pct":2,
            "worst_return_pct":-1,
            "best_return_pct":5,
            "worst_drawdown_pct":9,
            "average_sharpe":1,
        },
        "stability_gate":{"passed":True,"failed":[]},
    }

class Tests(unittest.TestCase):
    def test_features(self):
        self.assertEqual(derive_features(candidate())["strategy_id"],"MOMENTUM_10")
    def test_reasons(self):
        self.assertGreater(len(selection_reasons(derive_features(candidate()))),0)
    def test_risks(self):
        self.assertIsInstance(risk_factors(derive_features(candidate())),list)
    def test_confidence(self):
        f=derive_features(candidate())
        self.assertGreaterEqual(confidence_score(f,risk_factors(f))["score"],0)
    def test_description(self):
        self.assertIn("momentum",strategy_description("MOMENTUM_10",{"period":5}).lower())
    def test_summary(self):
        f=derive_features(candidate());r=selection_reasons(f);k=risk_factors(f);c=confidence_score(f,k)
        self.assertIn("MOMENTUM_10",build_summary(f,r,k,c))
    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(explain(Path(t))["state"],"AI_EXPLAINABILITY_SOURCE_REQUIRED")
    def test_safety(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(explain(Path(t))["order_submission_enabled"])
    def test_high_risk(self):
        f=derive_features(candidate());f["worst_window_drawdown_pct"]=40
        self.assertTrue(any(x["severity"]=="high" for x in risk_factors(f)))
    def test_confidence_level(self):
        f=derive_features(candidate());c=confidence_score(f,[])
        self.assertIn(c["level"],{"LOW","MEDIUM","HIGH"})

if __name__=="__main__":
    unittest.main()
