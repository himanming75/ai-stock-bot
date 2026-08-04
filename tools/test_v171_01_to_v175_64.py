import tempfile,unittest
from pathlib import Path
from controlled_micro_live.config import load,validate
from controlled_micro_live.kill_switch import load as load_kill,set_state
from controlled_micro_live.token import issue,inspect
from controlled_micro_live.dry_run import build
from controlled_micro_live.engine import evaluate

class Tests(unittest.TestCase):
    def test_safe_policy(self):
        with tempfile.TemporaryDirectory() as t:
            c=load(Path(t))
            self.assertTrue(c["dry_run_only"])
            self.assertFalse(c["live_submission_enabled"])
    def test_policy_validation(self):
        with tempfile.TemporaryDirectory() as t:self.assertTrue(validate(load(Path(t)))["valid"])
    def test_default_kill_switch_on(self):
        with tempfile.TemporaryDirectory() as t:self.assertTrue(load_kill(Path(t))["enabled"])
    def test_kill_switch_toggle(self):
        with tempfile.TemporaryDirectory() as t:self.assertFalse(set_state(Path(t),False,"TEST")["enabled"])
    def test_token_blocked_without_qualification(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            token=issue(root,{"symbol":"AAPL"},{"approved":True,"execution_authorized":False},False)
            self.assertFalse(token["eligible"])
    def test_dry_run_no_network(self):
        with tempfile.TemporaryDirectory() as t:
            r=build(Path(t),{"quantity":1,"estimated_notional":50},{})
            self.assertFalse(r["live_network_attempted"])
    def test_engine_live_zero(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(evaluate(Path(t))["actual_live_orders_submitted"],0)
    def test_engine_hard_blocked_empty(self):
        with tempfile.TemporaryDirectory() as t:self.assertEqual(evaluate(Path(t))["state"],"CONTROLLED_MICRO_LIVE_HARD_BLOCKED")

if __name__=="__main__":unittest.main()
