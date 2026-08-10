import json,tempfile,unittest
from pathlib import Path
from web_controller.backtest_api import _comparison

class TestStrategyComparison(unittest.TestCase):
    def test_wait_when_ai_not_ready(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            p=root/"runtime/ai_ml_model_health_v2_2_16/latest_ml_model_health.json"
            p.parent.mkdir(parents=True)
            p.write_text(json.dumps({"model_health":"YELLOW"}),encoding="utf-8")
            q=root/"runtime/ai_ml_research_recommendation_v2_2_22/latest_ml_research_recommendation.json"
            q.parent.mkdir(parents=True)
            q.write_text(json.dumps({"research_comparison_allowed":False}),encoding="utf-8")
            selected={
                "selection":{"strategy_id":"S1","dataset_id":"D1","window_id":"W1"},
                "result":{"status":"PASS","state":"READY","aggregation":{"top_result":{"automation_score":1.0}}}
            }
            c=_comparison(root,selected)
            self.assertEqual(c["recommendation"]["decision"],"KEEP_CURRENT_WAIT")
            self.assertIn("AI_RESEARCH_COMPARISON_NOT_READY",c["recommendation"]["reasons"])
            self.assertFalse(c["recommendation"]["automatic_strategy_change"])
            self.assertFalse(c["recommendation"]["automatic_live_execution_change"])

if __name__=="__main__":
    unittest.main()
