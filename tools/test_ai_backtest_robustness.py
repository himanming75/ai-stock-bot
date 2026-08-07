from pathlib import Path
import tempfile, unittest
import validation_analytics_v3 as a

class Tests(unittest.TestCase):
    def test_wilson_bounds(self):
        x=a.wilson_win_rate_interval(7,10)
        self.assertGreaterEqual(x["low"],0)
        self.assertLessEqual(x["high"],1)
        self.assertLess(x["low"],x["high"])

    def test_bootstrap_small_data_safe(self):
        x=a.bootstrap_expectancy_interval([1,2,3])
        self.assertEqual(x["status"],"INSUFFICIENT_DATA")

    def test_walk_forward_stability(self):
        wf={"windows":[
            {"oos_test_metrics":{"expectancy":1.0}},
            {"oos_test_metrics":{"expectancy":0.5}},
            {"oos_test_metrics":{"expectancy":-0.1}},
        ]}
        x=a.walk_forward_stability(wf)
        self.assertEqual(x["status"],"PASS")
        self.assertTrue(x["stable"])

    def test_scorecard_never_promotes(self):
        with tempfile.TemporaryDirectory() as td:
            r=a.main_report(Path(td))
            s=r["research_readiness_scorecard"]
            self.assertFalse(s["automatic_strategy_promotion"])
            self.assertFalse(s["automatic_parameter_change"])
            c=r["robustness_contracts"]
            self.assertFalse(c["broker_write_performed"])
            self.assertFalse(c["order_submission_performed"])
            self.assertFalse(c["paper_decision_path_changed"])

if __name__=="__main__":
    unittest.main()
