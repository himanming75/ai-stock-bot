from pathlib import Path
import unittest

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=Path("tools/run_regime_aware_shadow_v2_7.py").read_text(encoding="utf-8")

    def test_locked_candidates(self):
        self.assertIn('"MSFT_ONLY_30M"',self.t)
        self.assertIn('"MSFT_NVDA_30M"',self.t)
        self.assertIn('"dedup_minutes":15',self.t)
        self.assertIn('"horizon_minutes":30',self.t)
        self.assertIn('"cost_bps":5',self.t)

    def test_shadow_only(self):
        self.assertIn('"mode":"READ_ONLY_SHADOW"',self.t)
        self.assertIn('"automatic_promotion":False',self.t)

    def test_no_broker_code(self):
        for bad in ("TradingClient(","submit_order(","place_order(","MarketOrderRequest("):
            self.assertNotIn(bad,self.t)

    def test_canonical_reuse(self):
        self.assertIn("shadow.make_checkpoints",self.t)
        self.assertIn("shadow.analyze_at_rows",self.t)
        self.assertIn("shadow.truncate_by_checkpoint",self.t)

    def test_outcome_and_ledger(self):
        self.assertIn("SHADOW_SIGNAL",self.t)
        self.assertIn("SHADOW_OUTCOME",self.t)
        self.assertIn("shadow_candidate_ledger.jsonl",self.t)

if __name__=="__main__":
    unittest.main()
