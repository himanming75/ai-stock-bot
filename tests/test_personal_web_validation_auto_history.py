import json,tempfile,unittest
from pathlib import Path
from validation_automation.scheduler import save_snapshot,history_status,_compact_snapshot

class TestValidationAutoHistory(unittest.TestCase):
    def test_snapshot_history(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            payload={
                "progress":{
                    "trading_days_completed":1,"trading_days_target":10,
                    "resolved_outcomes":18,"resolved_outcomes_target":200,
                    "waiting_for_future_marks":102,"ai_health":"YELLOW",
                    "next_milestone":"COLLECT_9_MORE_VALIDATION_DAY(S)",
                    "blockers":["X"],
                },
                "ml":{"research_comparison_ready":False},
                "paper":{"passed":False},
            }
            snap=save_snapshot(root,payload,"test")
            self.assertEqual(snap["resolved_outcomes"],18)
            self.assertFalse(snap["synthetic_progress_used"])
            self.assertFalse(snap["future_outcomes_fabricated"])
            self.assertEqual(snap["paper_orders_submitted"],0)
            h=history_status(root)
            self.assertEqual(h["day_count"],1)
            self.assertEqual(h["latest"]["phase"],"test")

if __name__=="__main__":
    unittest.main()
