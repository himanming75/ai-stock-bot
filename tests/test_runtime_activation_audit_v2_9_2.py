from pathlib import Path
import unittest

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=Path("AUDIT_V2_9_2.ps1").read_text(encoding="utf-8")

    def test_exact_runner_detection(self):
        self.assertIn("RUN_PAPER_AUTONOMOUS_DAILY_SESSION.ps1",self.t)
        self.assertIn("EXACT_DAILY_SESSION_RUNNER",self.t)

    def test_read_only_task_audit(self):
        for bad in ("Enable-ScheduledTask","Start-ScheduledTask","Set-ScheduledTask","Register-ScheduledTask","Unregister-ScheduledTask"):
            self.assertNotIn(bad,self.t)

    def test_runtime_blockers_are_observed_only(self):
        self.assertIn("STALE_SESSION_LOCK",self.t)
        self.assertIn("stop_file_exists",self.t)
        self.assertIn("lock_file_removed = $false",self.t)
        self.assertIn("stop_file_removed = $false",self.t)

    def test_hook_integrity(self):
        self.assertIn("hook_method_count",self.t)
        self.assertIn("hook_call_count",self.t)
        self.assertIn("runner_compile_pass",self.t)

    def test_no_broker_or_order_actions(self):
        for bad in ("TradingClient(","submit_order(","MarketOrderRequest(","place_order("):
            self.assertNotIn(bad,self.t)

if __name__=="__main__":
    unittest.main()
