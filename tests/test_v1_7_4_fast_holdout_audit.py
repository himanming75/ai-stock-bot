from pathlib import Path
import unittest
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=Path("tools/audit_holdout_zero_trade_v1_7_4.py").read_text(encoding="utf-8")
    def test_recovery_reused_no_refetch(self):
        self.assertIn("v1_7_3_holdout_recovery",self.t)
        self.assertNotIn("StockHistoricalDataClient",self.t)
        self.assertNotIn("fetch_real_history",self.t)
    def test_fast_index(self):
        self.assertIn("bisect_right",self.t)
        self.assertIn("build_fast_index",self.t)
        self.assertIn("decision_cache",self.t)
    def test_canonical_reuse(self):
        for x in ("shadow.make_checkpoints","shadow.analyze_at_rows","shadow.rolling_lifecycle"):
            self.assertIn(x,self.t)
    def test_target_scope(self):
        self.assertIn('TARGET_START="2026-06-09"',self.t)
        self.assertIn('TARGET_END="2026-07-07"',self.t)
        self.assertIn("shadow.make_checkpoints=lambda _by:list(checkpoints)",self.t)
    def test_safety(self):
        for x in ("TradingClient(","submit_order(","place_order("):
            self.assertNotIn(x,self.t)
        self.assertIn('"network_used_by_audit":False',self.t)
if __name__=="__main__": unittest.main()
