import unittest
from ai_engine_v2.ml_feature_drift_status_v2_2_15 import build_v2_2_15_status

class TestV2215(unittest.TestCase):
    def test_contract(self):
        s=build_v2_2_15_status()
        self.assertEqual(s["status"],"PASS_DEVELOPMENT_COMPLETE")
        self.assertTrue(s["v2_2_9_training_features_reused"])
        self.assertTrue(s["v2_2_11_inference_features_reused"])
        self.assertTrue(s["mean_shift_monitoring"])
        self.assertTrue(s["median_iqr_shift_monitoring"])
        self.assertTrue(s["scale_ratio_monitoring"])
        self.assertTrue(s["feature_level_severity"])
        self.assertTrue(s["research_only"])
        self.assertFalse(s["automatic_retraining_allowed"])
        self.assertFalse(s["automatic_model_replacement_allowed"])
        self.assertFalse(s["execution_change_allowed"])
        self.assertFalse(s["selector_modified"])
        self.assertFalse(s["threshold_modified"])
        self.assertFalse(s["broker_network"])
        self.assertEqual(s["orders"],0)
        self.assertFalse(s["live_trading"])

if __name__=="__main__":
    unittest.main()
