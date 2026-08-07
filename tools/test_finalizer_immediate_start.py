from pathlib import Path
import unittest

class Tests(unittest.TestCase):
    def test_immediate_start_after_enable(self):
        txt=Path("RUN_FINALIZE_PAPER_VALIDATION_START.ps1").read_text(encoding="utf-8-sig")
        enable='Enable-ScheduledTask -TaskName "AIStockBot-PaperAutonomousDailySession"'
        start='Start-ScheduledTask -TaskName "AIStockBot-PaperAutonomousDailySession"'
        self.assertIn(enable,txt)
        self.assertIn(start,txt)
        self.assertGreater(txt.index(start),txt.index(enable))
        self.assertIn('PAPER ACCOUNT FLAT: PASS',txt)
        self.assertLess(txt.index('PAPER ACCOUNT FLAT: PASS'),txt.index(start))

    def test_live_remains_off(self):
        txt=Path("RUN_FINALIZE_PAPER_VALIDATION_START.ps1").read_text(encoding="utf-8-sig")
        self.assertIn('$env:LIVE_TRADING_ENABLED="false"',txt)
        self.assertIn('$env:ETRADE_LIVE_WRITE_ENABLED="false"',txt)
        self.assertIn('$env:ETRADE_LIVE_SUBMISSION_ENABLED="false"',txt)

if __name__=="__main__":
    unittest.main()
