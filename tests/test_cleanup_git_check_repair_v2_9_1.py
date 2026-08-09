from pathlib import Path
import unittest

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=Path("CLEANUP_V2_9_1.ps1").read_text(encoding="utf-8")

    def test_no_error_unmatch(self):
        self.assertNotIn("--error-unmatch",self.t)

    def test_safe_git_ls_files(self):
        self.assertIn('$Tracked = @(git ls-files -- "$Target")',self.t)
        self.assertIn("$Tracked.Count -gt 0",self.t)

    def test_tracked_refusal(self):
        self.assertIn("REFUSING TO REMOVE TRACKED PATH",self.t)

    def test_literal_path_delete(self):
        self.assertIn("Remove-Item -LiteralPath $Target -Recurse -Force",self.t)

    def test_known_cleanup_targets_only(self):
        self.assertIn("RUN_V2_8.ps1",self.t)
        self.assertIn("tools/summarize_shadow_v2_8.py",self.t)

if __name__=="__main__":
    unittest.main()
