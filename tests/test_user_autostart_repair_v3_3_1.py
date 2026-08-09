from pathlib import Path
import unittest

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.install=Path("INSTALL_DASHBOARD_USER_AUTOSTART_V3_3_1.ps1").read_text(encoding="utf-8")
        cls.verify=Path("VERIFY_V3_3_1.ps1").read_text(encoding="utf-8")

    def test_hkcu_run_used(self):
        self.assertIn("HKCU:", self.install)
        self.assertIn("CurrentVersion\\Run", self.install)

    def test_no_admin_task_registration(self):
        self.assertNotIn("Register-ScheduledTask", self.install)

    def test_points_to_existing_v33_launcher(self):
        self.assertIn("START_DASHBOARD_V3_3.ps1", self.install)

    def test_no_trading_commands(self):
        combined=self.install+self.verify
        for bad in ("submit_order","TradingClient","RUN_PAPER_AUTONOMOUS_DAILY_SESSION","Start-ScheduledTask"):
            self.assertNotIn(bad, combined)

    def test_verify_checks_entry(self):
        self.assertIn("AUTOSTART ENTRY: PASS", self.verify)

if __name__=="__main__":
    unittest.main()
