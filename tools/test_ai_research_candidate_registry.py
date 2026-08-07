from pathlib import Path
import tempfile, unittest
from tools.build_ai_research_candidate_registry import metric_score, classify_candidate, promotion_gate, build

class Tests(unittest.TestCase):
    def test_small_sample_not_ranked(self):
        self.assertIsNone(metric_score({"count":5,"expectancy":1,"win_rate":.8,"profit_factor":2}))

    def test_promising_candidate_is_research_only(self):
        row={"research_score":40}
        self.assertEqual(classify_candidate(row),"PROMISING_RESEARCH_ONLY")

    def test_gate_never_auto_promotes(self):
        g=promotion_gate({})
        self.assertTrue(g["manual_review_required"])
        self.assertFalse(g["automatic_strategy_promotion"])
        self.assertFalse(g["automatic_parameter_change"])
        self.assertFalse(g["automatic_risk_change"])
        self.assertEqual(g["order_path_effect"],"NONE")

    def test_build_contract_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            r=build(Path(td))
            c=r["contracts"]
            self.assertFalse(c["broker_write_performed"])
            self.assertFalse(c["order_submission_performed"])
            self.assertFalse(c["strategy_parameter_changed"])
            self.assertFalse(c["risk_parameter_changed"])
            self.assertFalse(c["paper_decision_path_changed"])
            self.assertFalse(c["live_decision_path_changed"])
            self.assertFalse(c["automatic_promotion"])

if __name__=="__main__":
    unittest.main()
