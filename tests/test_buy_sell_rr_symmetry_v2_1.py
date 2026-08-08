from pathlib import Path
import unittest
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=Path("tools/audit_buy_sell_rr_symmetry_v2_1.py").read_text(encoding="utf-8")
    def test_formula_symmetry_contract(self):
        self.assertIn('"engine_rr_formula":"abs(expected_return) / expected_risk"',self.t)
        self.assertIn('"formula_is_directionally_symmetric":True',self.t)
    def test_decomposition_dimensions(self):
        for x in ("abs_expected_return","expected_risk","reward_risk",
                  "alignment","disagreement","abs_consensus_score"):
            self.assertIn(x,self.t)
    def test_canonical_reuse(self):
        self.assertIn("shadow.analyze_at_rows",self.t)
        self.assertIn("shadow.make_checkpoints",self.t)
    def test_no_formula_change(self):
        self.assertIn('"rr_formula_changed":False',self.t)
        self.assertIn('"timeframe_weight_changed":False',self.t)
    def test_safety(self):
        for x in ("TradingClient(","submit_order(","place_order("):
            self.assertNotIn(x,self.t)
        self.assertIn('"network_used":False',self.t)
if __name__=="__main__": unittest.main()
