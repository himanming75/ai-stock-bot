
from pathlib import Path
import unittest

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = Path("dashboard/operations_dashboard_v3_2.py").read_text(encoding="utf-8")

    def test_git_discovery_exists(self):
        self.assertIn("def discover_git_executable()", self.t)
        self.assertIn('shutil.which("git")', self.t)

    def test_common_windows_git_path(self):
        self.assertIn(r"C:\Program Files\Git\cmd\git.exe", self.t)

    def test_missing_git_fallback(self):
        self.assertIn("GIT_EXECUTABLE_NOT_FOUND", self.t)
        self.assertIn('"available": False', self.t)

    def test_git_failure_does_not_crash(self):
        self.assertIn("except Exception:", self.t)
        self.assertIn('"synced": True if not head or not origin else head == origin', self.t)

    def test_read_only_unchanged(self):
        for bad in ("do_POST", "do_PUT", "do_DELETE", "TradingClient(", "submit_order(", "place_order("):
            self.assertNotIn(bad, self.t)

if __name__ == "__main__":
    unittest.main()
