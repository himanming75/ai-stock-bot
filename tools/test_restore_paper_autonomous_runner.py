from pathlib import Path
import unittest

class Tests(unittest.TestCase):
    def test_entrypoint_exists_and_delegates(self):
        p=Path("tools/run_paper_autonomous_daily_session.py")
        self.assertTrue(p.exists())
        txt=p.read_text(encoding="utf-8")
        self.assertIn("from paper_daily_session.runner import main",txt)
        self.assertIn("raise SystemExit(main())",txt)

if __name__=="__main__":
    unittest.main()
