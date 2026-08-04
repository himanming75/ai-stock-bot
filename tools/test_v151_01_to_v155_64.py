import os,tempfile,unittest
from pathlib import Path
from paper_web_ops.settings import load,validate,save
from paper_web_ops.state import build
from paper_web_ops.runner import execute

class Tests(unittest.TestCase):
    def test_default_submission_off(self):
        with tempfile.TemporaryDirectory() as t:self.assertFalse(load(Path(t))["paper_submission_enabled"])
    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:self.assertTrue(validate(load(Path(t)))["valid"])
    def test_live_setting_blocked(self):
        with tempfile.TemporaryDirectory() as t:
            c=load(Path(t));c["live_submission_enabled"]=True
            self.assertFalse(validate(c)["valid"])
    def test_state_live_zero(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(build(Path(t))["safety"]["actual_live_orders_submitted"],0)
    def test_missing_credentials(self):
        oldk=os.environ.pop("ALPACA_PAPER_API_KEY",None);olds=os.environ.pop("ALPACA_PAPER_SECRET_KEY",None)
        try:
            with tempfile.TemporaryDirectory() as t:self.assertEqual(execute(Path(t),"refresh_real_paper")["error"],"PAPER_CREDENTIALS_MISSING")
        finally:
            if oldk is not None:os.environ["ALPACA_PAPER_API_KEY"]=oldk
            if olds is not None:os.environ["ALPACA_PAPER_SECRET_KEY"]=olds
    def test_unknown_action(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(execute(Path(t),"live_order")["error"],"ACTION_NOT_ALLOWED")
    def test_confirmation_required(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);c=load(root);c["paper_submission_enabled"]=True;save(root,c)
            os.environ["ALPACA_PAPER_API_KEY"]="x";os.environ["ALPACA_PAPER_SECRET_KEY"]="y"
            r=execute(root,"submit_one_paper_cycle","WRONG")
            self.assertIn(r["error"],{"EMERGENCY_STOP_ENABLED","CONFIRMATION_REQUIRED"})

if __name__=="__main__":unittest.main()
