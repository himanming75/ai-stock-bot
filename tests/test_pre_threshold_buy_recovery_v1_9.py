from pathlib import Path
import unittest
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=Path("tools/analyze_pre_threshold_buy_recovery_v1_9.py").read_text(encoding="utf-8")
    def test_canonical_engine_reused(self):
        self.assertIn("shadow.analyze_at_rows",self.t)
        self.assertIn("shadow.make_checkpoints",self.t)
        self.assertNotIn("def analyze_symbol",self.t)
    def test_counterfactual_dimensions(self):
        for x in ("raw_confidence","calibrated_confidence","THRESHOLDS",
                  "warmup_normalization","msft_sell_bias_decomposition"):
            self.assertIn(x,self.t)
    def test_no_synthetic_warmup(self):
        self.assertIn('"synthetic_1d_data_created":False',self.t)
        self.assertIn('"warmup_data_imputed":False',self.t)
    def test_production_unchanged(self):
        self.assertIn('"threshold_change_applied_to_production":False',self.t)
        self.assertIn('"raw_confidence_applied_to_production":False',self.t)
    def test_safety(self):
        for x in ("TradingClient(","submit_order(","place_order("):
            self.assertNotIn(x,self.t)
        self.assertIn('"network_used":False',self.t)
if __name__=="__main__": unittest.main()
