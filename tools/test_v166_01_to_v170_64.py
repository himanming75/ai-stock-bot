import tempfile,unittest
from pathlib import Path
from live_approval.config import load,validate
from live_approval.comparison import compare
from live_approval.approval import create,decide
from live_approval.engine import evaluate

class Tests(unittest.TestCase):
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as t:
            c=load(Path(t))
            self.assertFalse(c["live_submission_enabled"])
            self.assertFalse(c["live_network_write_enabled"])
    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:self.assertTrue(validate(load(Path(t)))["valid"])
    def test_compare(self):
        r=compare({"equity":100},{"equity":90})
        self.assertEqual(r["equity_difference"],-10)
    def test_qualification_blocks(self):
        with tempfile.TemporaryDirectory() as t:
            r=create(Path(t),{"quantity":1,"estimated_notional":50},{"qualification":{"passed":False}})
            self.assertEqual(r["decision"],"BLOCKED")
    def test_decision_no_request(self):
        with tempfile.TemporaryDirectory() as t:self.assertFalse(decide(Path(t),"APPROVE")["ok"])
    def test_live_zero(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(evaluate(Path(t))["actual_live_orders_submitted"],0)
    def test_network_not_attempted(self):
        with tempfile.TemporaryDirectory() as t:self.assertFalse(evaluate(Path(t))["actual_live_network_attempted"])

if __name__=="__main__":unittest.main()
