from pathlib import Path
import tempfile, unittest
from tools.build_ai_candidate_cross_validation import compare_metrics, build

class Tests(unittest.TestCase):
    def test_insufficient_sample(self):
        x=compare_metrics(
            {"count":9,"expectancy":1,"win_rate":.6,"profit_factor":1.5},
            {"count":100,"expectancy":1,"win_rate":.6,"profit_factor":1.5},
        )
        self.assertEqual(x["status"],"INSUFFICIENT_DATA")

    def test_cross_validated(self):
        x=compare_metrics(
            {"count":20,"expectancy":.2,"win_rate":.60,"profit_factor":1.5},
            {"count":100,"expectancy":.15,"win_rate":.56,"profit_factor":1.4},
        )
        self.assertEqual(x["status"],"CROSS_VALIDATED_RESEARCH_ONLY")

    def test_divergent(self):
        x=compare_metrics(
            {"count":20,"expectancy":.2,"win_rate":.70,"profit_factor":1.5},
            {"count":100,"expectancy":-.3,"win_rate":.40,"profit_factor":.7},
        )
        self.assertEqual(x["status"],"DIVERGENT_RESEARCH_ONLY")

    def test_build_is_read_only(self):
        with tempfile.TemporaryDirectory() as td:
            r=build(Path(td))
            c=r["contracts"]
            self.assertFalse(c["broker_write_performed"])
            self.assertFalse(c["order_submission_performed"])
            self.assertFalse(c["task_change_performed"])
            self.assertFalse(c["strategy_parameter_changed"])
            self.assertFalse(c["risk_parameter_changed"])
            self.assertFalse(c["paper_decision_path_changed"])
            self.assertFalse(c["live_decision_path_changed"])
            self.assertFalse(c["automatic_candidate_promotion"])

if __name__=="__main__":
    unittest.main()
