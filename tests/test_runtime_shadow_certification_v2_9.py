from pathlib import Path
import unittest
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=Path("tools/certify_runtime_shadow_v2_9.py").read_text(encoding="utf-8")
        cls.p=Path("CLEANUP_V2_9.ps1").read_text(encoding="utf-8")
    def test_runner_integrity(self):
        self.assertIn("py_compile.compile",self.c)
        self.assertIn("method_marker_count",self.c)
        self.assertIn("call_marker_count",self.c)
    def test_runtime_waiting_is_valid(self):
        self.assertIn("PASS_WAITING_FOR_RUNTIME_OBSERVATION",self.c)
        self.assertIn('"zero_runtime_records_is_not_failure":True',self.c)
    def test_duplicate_checks(self):
        self.assertIn("duplicate_signal_ids",self.c)
        self.assertIn("duplicate_outcome_ids",self.c)
        self.assertIn("orphan_outcomes",self.c)
    def test_cleanup_only_untracked(self):
        self.assertIn("git ls-files --error-unmatch",self.p)
        self.assertIn("REFUSING TO REMOVE TRACKED PATH",self.p)
    def test_safety(self):
        for bad in ("TradingClient(","submit_order(","MarketOrderRequest(","place_order("):
            self.assertNotIn(bad,self.c)
if __name__=="__main__": unittest.main()
