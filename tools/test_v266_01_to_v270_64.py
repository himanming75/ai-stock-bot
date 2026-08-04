import os, tempfile, time, unittest
from pathlib import Path
from windows_autostart_recovery.config import load, validate
from windows_autostart_recovery.recovery import inspect
from windows_autostart_recovery.stale_lock import remove_if_stale
from windows_autostart_recovery.logs import cleanup
from windows_autostart_recovery.supervisor import run

class Tests(unittest.TestCase):
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as t:
            p = load(Path(t))
            self.assertFalse(p["supervisor_enabled"])
            self.assertFalse(p["live_submission_enabled"])

    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(validate(load(Path(t)))["valid"])

    def test_recovery_plan(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(inspect(Path(t))["automatic_live_resume_allowed"])

    def test_stale_lock(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "lock"
            path.write_text("1")
            old = time.time() - 3600
            os.utime(path, (old, old))
            self.assertTrue(remove_if_stale(path, 1)["removed"])

    def test_log_cleanup(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            old = d / "old.log"
            old.write_text("x")
            stamp = time.time() - 3 * 86400
            os.utime(old, (stamp, stamp))
            self.assertIn("old.log", cleanup(d, 1)["removed"])

    def test_default_blocked(self):
        with tempfile.TemporaryDirectory() as t:
            result = run(Path(t), execute_child=False)
            self.assertIn("SUPERVISOR_DISABLED", result["blocking_reasons"])
            self.assertEqual(result["actual_live_orders_submitted"], 0)

if __name__ == "__main__":
    unittest.main()
