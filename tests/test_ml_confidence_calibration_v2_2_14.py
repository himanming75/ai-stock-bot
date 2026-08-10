import unittest
from ai_engine_v2.ml_confidence_calibration_status_v2_2_14 import build_v2_2_14_status

class TestV2214(unittest.TestCase):
    def test_contract(self):
        s=build_v2_2_14_status()
        self.assertEqual(s["status"],"PASS_DEVELOPMENT_COMPLETE")
        self.assertTrue(s["v2_2_12_probability_outcomes_reused"])
        self.assertTrue(s["v2_2_13_readiness_gate_reused"])
        self.assertTrue(s["ten_bin_reliability"])
        self.assertTrue(s["expected_calibration_error"])
        self.assertTrue(s["multiclass_brier_score"])
        self.assertTrue(s["overconfidence_measure"])
        self.assertTrue(s["research_only"])
        self.assertFalse(s["execution_use_allowed"])
        self.assertFalse(s["selector_modified"])
        self.assertFalse(s["threshold_modified"])
        self.assertFalse(s["model_modified"])
        self.assertFalse(s["model_promotion_allowed"])
        self.assertFalse(s["broker_network"])
        self.assertEqual(s["orders"],0)
        self.assertFalse(s["live_trading"])

if __name__=="__main__":
    unittest.main()
