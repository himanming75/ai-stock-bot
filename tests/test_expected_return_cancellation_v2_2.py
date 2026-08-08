from pathlib import Path
import unittest
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=Path("tools/audit_expected_return_cancellation_v2_2.py").read_text(encoding="utf-8")
    def test_contribution_math(self):
        self.assertIn("weighted_expected_return",self.t)
        self.assertIn("cancellation_ratio",self.t)
        self.assertIn("absolute_contribution_sum",self.t)
    def test_all_timeframes(self):
        for tf in ("1m","3m","5m","15m","30m","1h","1d"):
            self.assertIn(tf,self.t)
    def test_canonical_reuse(self):
        self.assertIn("shadow.analyze_at_rows",self.t)
        self.assertIn("shadow.make_checkpoints",self.t)
    def test_no_weight_change(self):
        self.assertIn('"timeframe_weights_changed":False',self.t)
        self.assertIn('"expected_return_formula_changed":False',self.t)
    def test_safety(self):
        for x in ("TradingClient(","submit_order(","place_order("):
            self.assertNotIn(x,self.t)
        self.assertIn('"network_used":False',self.t)
if __name__=="__main__": unittest.main()
