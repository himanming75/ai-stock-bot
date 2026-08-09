from pathlib import Path
import unittest

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=Path("RECOVER_V2_9_3.ps1").read_text(encoding="utf-8")

    def test_live_pid_blocks(self):
        self.assertIn("BLOCKED_LOCK_PROCESS_IS_ALIVE",self.t)
        self.assertIn("Get-Process -Id $PidValue",self.t)

    def test_backup_before_delete(self):
        self.assertIn("Copy-Item -LiteralPath $LockPath",self.t)
        self.assertIn("Remove-Item -LiteralPath $LockPath -Force",self.t)
        self.assertLess(self.t.index("Copy-Item -LiteralPath $LockPath"), self.t.index("Remove-Item -LiteralPath $LockPath -Force"))

    def test_no_task_start_or_modify(self):
        for bad in ("Start-ScheduledTask","Enable-ScheduledTask","Set-ScheduledTask","Register-ScheduledTask"):
            self.assertNotIn(bad,self.t)

    def test_no_stop_delete(self):
        self.assertIn("stop_file_removed = $false",self.t)
        self.assertNotIn('Remove-Item "$Repo\\runtime\\paper_autonomous_daily_session\\STOP"', self.t)

    def test_safety_contract(self):
        self.assertIn("paper_order_submission_performed = $false",self.t)
        self.assertIn("live_order_submission_performed = $false",self.t)

if __name__=="__main__":
    unittest.main()
