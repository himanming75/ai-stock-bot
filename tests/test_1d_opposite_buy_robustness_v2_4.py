from pathlib import Path
import unittest
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=Path("tools/audit_1d_opposite_buy_robustness_v2_4.py").read_text(encoding="utf-8")
    def test_stress_dimensions(self):
        for x in ("DEDUP_WINDOWS_MIN","ENTRY_DELAYS","ROUND_TRIP_COSTS_BPS","HORIZONS"):
            self.assertIn(x,self.t)
    def test_only_1d_opposite(self):
        self.assertIn('classify_1d(item)!="1D_OPPOSITE_SELL"',self.t)
    def test_no_production_change(self):
        self.assertIn('"dedup_rule_applied_to_production":False',self.t)
        self.assertIn('"cost_model_applied_to_production":False',self.t)
    def test_canonical_reuse(self):
        self.assertIn("shadow.analyze_at_rows",self.t)
        self.assertIn("shadow.make_checkpoints",self.t)
    def test_safety(self):
        for x in ("TradingClient(","submit_order(","place_order("):
            self.assertNotIn(x,self.t)
        self.assertIn('"network_used":False',self.t)
if __name__=="__main__": unittest.main()
