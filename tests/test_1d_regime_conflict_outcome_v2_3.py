from pathlib import Path
import unittest
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=Path("tools/audit_1d_regime_conflict_outcome_v2_3.py").read_text(encoding="utf-8")
    def test_groups(self):
        for x in ("1D_ALIGNED_BUY","1D_HOLD","1D_OPPOSITE_SELL"):
            self.assertIn(x,self.t)
    def test_top_scenario(self):
        self.assertIn("TP_PCT=0.015",self.t)
        self.assertIn("SL_PCT=0.0075",self.t)
        self.assertIn("MAX_HOLD_MINUTES=45",self.t)
    def test_conservative_path_rule(self):
        self.assertIn("SL_FIRST_CONSERVATIVE",self.t)
        self.assertIn("if sl_hit:",self.t)
    def test_no_production_change(self):
        self.assertIn('"one_day_weight_changed":False',self.t)
        self.assertIn('"production_change_applied":False',self.t)
    def test_safety(self):
        for x in ("TradingClient(","submit_order(","place_order("):
            self.assertNotIn(x,self.t)
        self.assertIn('"network_used":False',self.t)
if __name__=="__main__": unittest.main()
