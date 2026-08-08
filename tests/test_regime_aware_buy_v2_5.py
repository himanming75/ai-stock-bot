from pathlib import Path
import unittest

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=Path("tools/audit_regime_aware_buy_v2_5.py").read_text(encoding="utf-8")

    def test_symbol_groups(self):
        for x in ("MSFT_NVDA","MSFT_ONLY","NVDA_ONLY","AAPL_ONLY"):
            self.assertIn(x,self.t)

    def test_stress_matrix(self):
        for x in ("HORIZONS","ROUND_TRIP_COSTS_BPS","DEDUP_MINUTES","scenario_matrix"):
            self.assertIn(x,self.t)

    def test_lifecycle_contract(self):
        self.assertIn("TP_PCT=0.015",self.t)
        self.assertIn("SL_PCT=0.0075",self.t)
        self.assertIn("MAX_HOLD_MINUTES=45",self.t)

    def test_no_production_change(self):
        self.assertIn('"regime_rule_applied_to_production":False',self.t)
        self.assertIn('"production_change_applied":False',self.t)

    def test_safety(self):
        for x in ("TradingClient(","submit_order(","place_order("):
            self.assertNotIn(x,self.t)
        self.assertIn('"network_used":False',self.t)

if __name__=="__main__":
    unittest.main()
