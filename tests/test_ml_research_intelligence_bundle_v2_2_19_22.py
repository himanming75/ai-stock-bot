import unittest
from ai_engine_v2.ml_research_intelligence_bundle_status_v2_2_19_22 import build_status
class TestBundle(unittest.TestCase):
    def test_contract(self):
        s=build_status()
        self.assertEqual(s["status"],"PASS_DEVELOPMENT_COMPLETE")
        self.assertTrue(s["horizon_consensus"])
        self.assertTrue(s["uncertainty_scoring"])
        self.assertTrue(s["regime_segmentation"])
        self.assertTrue(s["research_recommendation_snapshot"])
        self.assertTrue(s["research_only"])
        self.assertFalse(s["automatic_execution_change"])
        self.assertFalse(s["automatic_selector_change"])
        self.assertFalse(s["automatic_threshold_change"])
        self.assertFalse(s["automatic_model_promotion"])
        self.assertFalse(s["broker_network"])
        self.assertEqual(s["orders"],0)
        self.assertFalse(s["live_trading"])
if __name__=="__main__": unittest.main()
