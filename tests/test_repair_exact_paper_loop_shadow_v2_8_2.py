from pathlib import Path
import unittest
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t=Path("tools/repair_exact_paper_loop_shadow_v2_8_2.py").read_text(encoding="utf-8")
    def test_restores_backup_first(self):
        self.assertIn("shutil.copy2(backup,target)",self.t)
        self.assertIn('report["restored_from_backup"]=True',self.t)
    def test_real_newline_fix(self):
        self.assertIn('METHOD_BLOCK + "\\n" + method_anchor',self.t)
        self.assertIn("BLOCKED_LITERAL_BACKSLASH_N_REMAINS",self.t)
    def test_compile_gate(self):
        self.assertIn("py_compile.compile",self.t)
        self.assertIn("PASS_REPAIRED_AND_INTEGRATED",self.t)
    def test_safety(self):
        for bad in ("TradingClient(","submit_order(","MarketOrderRequest(","place_order("):
            self.assertNotIn(bad,self.t)
    def test_existing_loop_only(self):
        self.assertIn('"existing_poll_loop_reused":True',self.t)
        self.assertIn('"production_selector_changed":False',self.t)
if __name__=="__main__": unittest.main()
