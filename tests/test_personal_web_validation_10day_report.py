import json,tempfile,unittest
from pathlib import Path
from validation_automation.scheduler import save_snapshot
from web_controller.validation_lab_api import _validation_report

class TestValidation10DayReport(unittest.TestCase):
    def test_report_from_real_history_only(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            payload={
                "progress":{
                    "trading_days_completed":1,
                    "trading_days_target":10,
                    "resolved_outcomes":18,
                    "resolved_outcomes_target":200,
                    "waiting_for_future_marks":102,
                    "ai_health":"YELLOW",
                    "next_milestone":"COLLECT_9_MORE_VALIDATION_DAY(S)",
                    "blockers":["X"],
                },
                "ml":{"research_comparison_ready":False},
                "paper":{"passed":False},
            }
            save_snapshot(root,payload,"test")
            r=_validation_report(root)
            self.assertEqual(r["history_days"],1)
            self.assertEqual(r["latest_resolved_outcomes"],18)
            self.assertEqual(r["latest_waiting_future_marks"],102)
            self.assertEqual(r["latest_ai_health"],"YELLOW")
            self.assertFalse(r["synthetic_days_added"])
            self.assertFalse(r["interpolation_used"])
            self.assertFalse(r["future_outcomes_fabricated"])
            self.assertEqual(len(r["points"]),1)

if __name__=="__main__":
    unittest.main()
