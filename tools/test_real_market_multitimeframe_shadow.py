from pathlib import Path
import unittest

class Tests(unittest.TestCase):
    def test_shadow_reuses_canonical_functions(self):
        txt=Path("tools/build_real_market_multitimeframe_shadow.py").read_text(encoding="utf-8")
        self.assertIn("from multi_timeframe_ai.engine import analyze_symbol",txt)
        self.assertIn("from paper_autonomous_execution.signals import select_candidate",txt)
        self.assertIn('"live_equivalence_asserted":False',txt)

    def test_no_write_surface(self):
        txt=Path("tools/build_real_market_multitimeframe_shadow.py").read_text(encoding="utf-8")
        self.assertNotIn("submit_order(",txt)
        self.assertNotIn("TradingClient(",txt)
        self.assertNotIn("Start-ScheduledTask",txt)
        self.assertIn('"paper_task_modified":False',txt)

if __name__=="__main__":
    unittest.main()
