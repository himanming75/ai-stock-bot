import tempfile,unittest
from pathlib import Path
from production_scheduler.config import load,validate
from production_scheduler.lock import acquire,release
from production_scheduler.plan import build
from production_scheduler.jobs import run
from production_scheduler.engine import evaluate

class Tests(unittest.TestCase):
    def test_defaults_safe(self):
        with tempfile.TemporaryDirectory() as t:
            c=load(Path(t))
            self.assertFalse(c["scheduled_paper_submission_enabled"])
            self.assertFalse(c["scheduled_live_submission_enabled"])
    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:self.assertTrue(validate(load(Path(t)))["valid"])
    def test_duplicate_lock(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            self.assertTrue(acquire(root,"x",30)["acquired"])
            self.assertFalse(acquire(root,"x",30)["acquired"])
            release(root,"x")
    def test_plan_no_orders(self):
        with tempfile.TemporaryDirectory() as t:self.assertFalse(build(Path(t))["scheduled_order_submission_included"])
    def test_unknown_job(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(run(Path(t),"live_order")["error"],"JOB_NOT_ALLOWED")
    def test_engine_live_zero(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(evaluate(Path(t))["actual_live_orders_submitted"],0)
    def test_engine_ready(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(evaluate(Path(t))["state"],"PRODUCTION_SCHEDULER_READY")

if __name__=="__main__":unittest.main()
