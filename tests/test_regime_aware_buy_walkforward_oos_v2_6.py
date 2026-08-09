from pathlib import Path
import unittest

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=Path("tools/audit_regime_aware_buy_walkforward_oos_v2_6.py").read_text(encoding="utf-8")

    def test_candidates_locked(self):
        self.assertIn('"MSFT_ONLY_30M"',self.t)
        self.assertIn('"MSFT_NVDA_30M"',self.t)
        self.assertIn('"candidate_selection_reopened":False',self.t)

    def test_walkforward(self):
        self.assertIn("WINDOW_TRADING_DAYS=5",self.t)
        self.assertIn("chunk_dates",self.t)
        self.assertIn("positive_window_rate",self.t)

    def test_cost_stress(self):
        self.assertIn("COST_BPS=(5,10)",self.t)

    def test_no_production_change(self):
        self.assertIn('"candidate_reoptimized":False',self.t)
        self.assertIn('"production_change_applied":False',self.t)

    def test_safety(self):
        for x in ("TradingClient(","submit_order(","place_order("):
            self.assertNotIn(x,self.t)
        self.assertIn('"network_used":False',self.t)

if __name__=="__main__":
    unittest.main()
