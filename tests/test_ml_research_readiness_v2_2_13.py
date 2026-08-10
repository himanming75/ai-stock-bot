import unittest
from ai_engine_v2.ml_research_readiness_status_v2_2_13 import build_v2_2_13_status

class TestV2213(unittest.TestCase):
    def test_contract(self):
        s=build_v2_2_13_status()
        self.assertEqual(s["status"],"PASS_DEVELOPMENT_COMPLETE")
        self.assertTrue(s["v2_2_12_outcomes_reused"])
        self.assertTrue(s["minimum_total_sample_gate"])
        self.assertTrue(s["minimum_per_horizon_gate"])
        self.assertTrue(s["edge_ready_sample_gate"])
        self.assertTrue(s["actual_class_coverage_gate"])
        self.assertTrue(s["research_readiness_only"])
        self.assertFalse(s["selector_change_allowed"])
        self.assertFalse(s["threshold_change_allowed"])
        self.assertFalse(s["model_promotion_allowed"])
        self.assertFalse(s["paper_execution_change_allowed"])
        self.assertFalse(s["broker_network"])
        self.assertEqual(s["orders"],0)
        self.assertFalse(s["live_trading"])

if __name__=="__main__":
    unittest.main()
