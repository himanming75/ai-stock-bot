import tempfile,unittest
from pathlib import Path
from operations_manager.config import load,validate,save
from operations_manager.lock import acquire,release
from operations_manager.health import evaluate
from operations_manager.recovery import create_plan
from operations_manager.jobs import run

class Tests(unittest.TestCase):
    def test_defaults_safe(self):
        with tempfile.TemporaryDirectory() as t:
            c=load(Path(t))
            self.assertFalse(c["automated_paper_submission_enabled"])
            self.assertFalse(c["live_submission_enabled"])
    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(validate(load(Path(t)))["valid"])
    def test_scheduled_submission_blocked(self):
        with tempfile.TemporaryDirectory() as t:
            c=load(Path(t));c["automated_paper_submission_enabled"]=True
            self.assertFalse(validate(c)["valid"])
    def test_lock_duplicate(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            self.assertTrue(acquire(root,"x")["acquired"])
            self.assertFalse(acquire(root,"x")["acquired"])
            release(root,"x")
    def test_health_live_zero(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["actual_live_orders_submitted"],0)
    def test_recovery_no_live(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(create_plan(Path(t))["live_actions_included"])
    def test_unknown_job(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(run(Path(t),"live_order")["error"],"JOB_NOT_ALLOWED")

if __name__=="__main__":unittest.main()
