import tempfile,unittest
from pathlib import Path
from strategy_manager.config import load,validate,save,restore
from strategy_manager.apply import build_runtime_policy

class Tests(unittest.TestCase):
    def test_default(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(load(Path(t))["paper_only"])
    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(validate(load(Path(t)))["valid"])
    def test_requires_strategy(self):
        with tempfile.TemporaryDirectory() as t:
            c=load(Path(t))
            for v in c["strategies"].values():v["enabled"]=False
            self.assertFalse(validate(c)["valid"])
    def test_live_disabled(self):
        with tempfile.TemporaryDirectory() as t:
            c=load(Path(t));c["live_submission_enabled"]=True
            self.assertFalse(validate(c)["valid"])
    def test_save_backup_restore(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);c=load(root);c["symbols"]=["AAPL"]
            self.assertTrue(save(root,c)["ok"])
            c["symbols"]=["MSFT"];save(root,c)
            self.assertTrue(restore(root)["ok"])
    def test_runtime_live_zero(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(build_runtime_policy(Path(t))["actual_live_orders_submitted"],0)

if __name__=="__main__":unittest.main()
