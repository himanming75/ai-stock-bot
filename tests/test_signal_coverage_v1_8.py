from pathlib import Path
import unittest
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=Path("tools/analyze_signal_coverage_v1_8.py").read_text(encoding="utf-8")
    def test_reuses_v17_result(self):
        self.assertIn("latest_holdout_zero_trade_audit_v1_7_4.json",self.t)
        self.assertNotIn("StockHistoricalDataClient",self.t)
        self.assertNotIn("fetch_real_history",self.t)
    def test_dimensions(self):
        for x in ("sell_decomposition","confidence_decomposition","reward_risk_decomposition",
                  "hold_decomposition","feature_coverage_decomposition","buy_like_but_blocked"):
            self.assertIn(x,self.t)
    def test_no_threshold_change(self):
        self.assertIn('"thresholds_changed":False',self.t)
        self.assertIn('"counterfactual_threshold_relaxation_performed":False',self.t)
    def test_safety(self):
        for x in ("TradingClient(","submit_order(","place_order("):
            self.assertNotIn(x,self.t)
        self.assertIn('"network_used":False',self.t)
    def test_no_duplicate_engine(self):
        self.assertIn('"duplicate_engine_created":False',self.t)
if __name__=="__main__": unittest.main()
