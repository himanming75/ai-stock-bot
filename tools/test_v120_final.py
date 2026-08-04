import tempfile,unittest
from pathlib import Path
from v120_final_release.integration import evaluate_stages
from v120_final_release.safety import evaluate_safety
from v120_final_release.inventory import build_inventory,verify_inventory
from v120_final_release.bundle import create_bundle
from v120_final_release.engine import evaluate

class Tests(unittest.TestCase):
    def test_missing_stages(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(evaluate_stages(Path(t))["passed"])
    def test_safety_blocks_missing(self):
        self.assertFalse(evaluate_safety({"passed":False,"rows":[]})["passed"])
    def test_inventory(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); (p/"a.txt").write_text("a")
            inv=build_inventory(p)
            self.assertTrue(verify_inventory(p,inv)["passed"])
    def test_bundle(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t); (p/"a.txt").write_text("a")
            out=p/"out"/"x.zip"
            self.assertTrue(create_bundle(p,out)["created"])
    def test_missing_source_review(self):
        with tempfile.TemporaryDirectory() as t:
            r=evaluate(Path(t))
            self.assertFalse(r["development_complete"])
    def test_orders_zero(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["actual_orders_submitted"],0)
    def test_live_disabled(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(evaluate(Path(t))["live_trading_ready"])

if __name__=="__main__": unittest.main()
