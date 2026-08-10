import unittest
from ai_engine_v2.ml_prediction_outcome_status_v2_2_12 import build_v2_2_12_status

class TestV2212(unittest.TestCase):
    def test_contract(self):
        s=build_v2_2_12_status()
        self.assertEqual(s["status"],"PASS_DEVELOPMENT_COMPLETE")
        self.assertTrue(s["v2_2_11_inference_ledger_reused"])
        self.assertTrue(s["v2_2_8_1_market_bars_reused"])
        self.assertEqual(s["forward_horizons"],[5,15,30,60])
        self.assertTrue(s["real_future_market_marks_only"])
        self.assertTrue(s["direction_accuracy_metrics"])
        self.assertTrue(s["edge_ready_segment_metrics"])
        self.assertTrue(s["deduplicated_outcome_ledger"])
        self.assertTrue(s["research_only"])
        self.assertFalse(s["selector_change_recommendation_enabled"])
        self.assertFalse(s["model_promotion_enabled"])
        self.assertFalse(s["execution_selector_modified"])
        self.assertFalse(s["broker_network"])
        self.assertEqual(s["paper_orders"],0)
        self.assertEqual(s["live_orders"],0)
        self.assertFalse(s["live_trading"])

if __name__=="__main__":
    unittest.main()
