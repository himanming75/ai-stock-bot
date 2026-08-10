import unittest
from pathlib import Path
import inspect

class TestValidationSchedulerBackendRepair(unittest.TestCase):
    def test_backend_contract(self):
        root=Path(r"C:\stock-bot")
        api=(root/"web_controller/validation_lab_api.py").read_text(encoding="utf-8")
        scheduler=(root/"validation_automation/scheduler.py").read_text(encoding="utf-8")

        self.assertIn('"scheduler":_scheduler_status(root)',api)
        self.assertIn('"history":_history_status(root)',api)
        self.assertIn('action=="start_auto_scheduler"',api)
        self.assertIn('action=="stop_auto_scheduler"',api)
        self.assertIn('action=="run_daily_snapshot_now"',api)

        self.assertIn("def start_scheduler",scheduler)
        self.assertIn("def stop_scheduler",scheduler)
        self.assertIn("def run_and_snapshot",scheduler)
        self.assertIn("def history_status",scheduler)

    def test_runtime_payload_has_scheduler(self):
        root=Path(r"C:\stock-bot")
        from web_controller.validation_lab_api import get_payload
        d=get_payload(root)
        self.assertIn("scheduler",d)
        self.assertIn("history",d)
        self.assertIn("running",d["scheduler"])
        self.assertIn("recent",d["history"])

if __name__=="__main__":
    unittest.main()
