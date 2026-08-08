from pathlib import Path
import unittest
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=Path("tools/audit_buy_rejection_funnel_v2_0.py").read_text(encoding="utf-8")
    def test_funnel_buckets(self):
        for x in ("FAIL_CONFIDENCE_AND_RR","FAIL_CONFIDENCE_ONLY","FAIL_RR_ONLY",
                  "PASS_ALL_BUT_LOST_TO_SELL_RANKING","PASS_ALL_AND_WINNER"):
            self.assertIn(x,self.t)
    def test_thresholds_observed_only(self):
        self.assertIn('"threshold_change_applied":False',self.t)
        self.assertIn('"selector_ranking_change_applied":False',self.t)
        self.assertIn('"reward_risk_formula_change_applied":False',self.t)
    def test_canonical_reuse(self):
        self.assertIn("shadow.analyze_at_rows",self.t)
        self.assertIn("shadow.make_checkpoints",self.t)
    def test_no_duplicate_selector(self):
        self.assertNotIn("def select_candidate",self.t)
        self.assertIn("rank_key",self.t)
    def test_safety(self):
        for x in ("TradingClient(","submit_order(","place_order("):
            self.assertNotIn(x,self.t)
        self.assertIn('"network_used":False',self.t)
if __name__=="__main__": unittest.main()
