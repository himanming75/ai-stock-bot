import unittest

from ai_engine_v2.ml_shadow_inference_status_v2_2_11 import build_v2_2_11_status


class TestMLShadowInferenceV2211(unittest.TestCase):
    def test_development_contract(self):
        s=build_v2_2_11_status()
        self.assertEqual(s["status"],"PASS_DEVELOPMENT_COMPLETE")
        self.assertTrue(s["v2_2_8_1_exact_feature_engineering_reused"])
        self.assertTrue(s["v2_2_10_selected_models_reused"])
        self.assertTrue(s["model_sha256_verified_before_load"])
        self.assertEqual(s["multi_horizon_inference"],[5,15,30,60])
        self.assertTrue(s["research_ranking_only"])
        self.assertTrue(s["shadow_only"])
        self.assertFalse(s["automatic_promotion"])
        self.assertFalse(s["execution_selector_modified"])
        self.assertFalse(s["broker_network"])
        self.assertEqual(s["paper_orders"],0)
        self.assertEqual(s["live_orders"],0)
        self.assertFalse(s["live_trading"])


if __name__=="__main__":
    unittest.main()
