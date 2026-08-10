import unittest
from pathlib import Path
from web_controller.validation_lab_api import _final_qualification

class TestFinalQualification(unittest.TestCase):
    def safety(self):
        return {
            "live_orders_submitted_by_validation_lab":0,
            "paper_orders_submitted_by_validation_lab":0,
            "automatic_model_promotion":False,
            "automatic_strategy_change":False,
            "automatic_threshold_change":False,
        }

    def test_continue_when_incomplete(self):
        report={
            "validation_days_completed":1,"validation_days_target":10,
            "latest_resolved_outcomes":18,"resolved_outcomes_target":200,
            "latest_waiting_future_marks":102,
            "latest_ai_health":"YELLOW",
            "latest_research_comparison_ready":False,
            "latest_paper_qualified":False,
            "synthetic_days_added":False,
            "interpolation_used":False,
            "future_outcomes_fabricated":False,
        }
        q=_final_qualification(Path(r"C:\stock-bot"),report,{},{"passed":False},self.safety())
        self.assertEqual(q["decision"],"CONTINUE")
        self.assertEqual(q["hard_fail_count"],0)
        self.assertFalse(q["automatic_promotion"])

    def test_pass_when_all_gates(self):
        report={
            "validation_days_completed":10,"validation_days_target":10,
            "latest_resolved_outcomes":250,"resolved_outcomes_target":200,
            "latest_waiting_future_marks":0,
            "latest_ai_health":"GREEN",
            "latest_research_comparison_ready":True,
            "latest_paper_qualified":True,
            "synthetic_days_added":False,
            "interpolation_used":False,
            "future_outcomes_fabricated":False,
        }
        q=_final_qualification(Path(r"C:\stock-bot"),report,{},{"passed":True},self.safety())
        self.assertEqual(q["decision"],"PASS")
        self.assertEqual(q["gates_passed"],5)
        self.assertFalse(q["automatic_promotion"])

    def test_fail_on_integrity_violation(self):
        report={
            "validation_days_completed":10,"validation_days_target":10,
            "latest_resolved_outcomes":250,"resolved_outcomes_target":200,
            "latest_ai_health":"GREEN",
            "latest_research_comparison_ready":True,
            "latest_paper_qualified":True,
            "synthetic_days_added":True,
            "interpolation_used":False,
            "future_outcomes_fabricated":False,
        }
        q=_final_qualification(Path(r"C:\stock-bot"),report,{},{"passed":True},self.safety())
        self.assertEqual(q["decision"],"FAIL")
        self.assertGreater(q["hard_fail_count"],0)

if __name__=="__main__":
    unittest.main()
