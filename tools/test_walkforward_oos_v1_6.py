from pathlib import Path
import unittest
class Tests(unittest.TestCase):
 def setUp(self): self.text=Path("tools/build_real_market_multitimeframe_shadow.py").read_text(encoding="utf-8")
 def test_mode(self): self.assertIn("def walkforward_oos(",self.text); self.assertIn('"walkforward"',self.text)
 def test_holdout(self): self.assertIn("AI_STOCK_DISCOVERY_START_DATE",self.text); self.assertIn("pre_discovery_trading_dates",self.text)
 def test_reuse(self): self.assertIn("report=rolling_lifecycle(root)",self.text)
 def test_scenarios(self):
  for n in ("BASELINE","EXCLUDE_MSFT","NO_NEW_ENTRY_AFTER_14_ET","EXCLUDE_MSFT_AND_NO_ENTRY_AFTER_14_ET","MAX_HOLD_20M","MAX_HOLD_45M","MAX_HOLD_60M"): self.assertIn(n,self.text)
 def test_safety(self): self.assertIn('"automatic_promotion":False',self.text); self.assertNotIn("TradingClient(",self.text)
if __name__=="__main__": unittest.main()
