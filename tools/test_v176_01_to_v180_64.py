import tempfile,unittest
from pathlib import Path
from restricted_live_automation.config import load,validate
from restricted_live_automation.gate import evaluate as gate
from restricted_live_automation.plan import build
from restricted_live_automation.engine import evaluate

class Tests(unittest.TestCase):
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as t:
            c=load(Path(t))
            self.assertFalse(c["automatic_submission_enabled"])
            self.assertFalse(c["live_submission_enabled"])
    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:self.assertTrue(validate(load(Path(t)))["valid"])
    def test_empty_gate_blocked(self):
        with tempfile.TemporaryDirectory() as t:
            p=load(Path(t))
            self.assertFalse(gate(p,{}, {}, {})["passed"])
    def test_plan_no_broker_submission(self):
        p=build({},{"passed":False})
        self.assertFalse(p["broker_submission_step_included"])
    def test_live_zero(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(evaluate(Path(t))["actual_live_orders_submitted"],0)
    def test_hard_blocked_empty(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(evaluate(Path(t))["state"],"RESTRICTED_LIVE_AUTOMATION_HARD_BLOCKED")

if __name__=="__main__":unittest.main()
