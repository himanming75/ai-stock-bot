import tempfile, unittest
from pathlib import Path
from autonomous_paper_session.config import load, validate
from autonomous_paper_session.lock import SessionLock
from autonomous_paper_session.stop import request, clear, requested
from autonomous_paper_session.runner import run

def fake_cycle(root: Path, allow_network: bool) -> dict:
    return {
        "state": "FAKE",
        "market_open": False,
        "actual_paper_orders_submitted": 0,
        "actual_live_orders_submitted": 0,
    }

class Tests(unittest.TestCase):
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as t:
            p = load(Path(t))
            self.assertFalse(p["session_runner_enabled"])
            self.assertFalse(p["allow_real_paper_network"])

    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(validate(load(Path(t)))["valid"])

    def test_lock(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "lock"
            first = SessionLock(path)
            second = SessionLock(path)
            self.assertTrue(first.acquire())
            self.assertFalse(second.acquire())
            first.release()

    def test_stop_file(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            clear(root)
            self.assertFalse(requested(root))
            request(root)
            self.assertTrue(requested(root))

    def test_default_runner_blocked(self):
        with tempfile.TemporaryDirectory() as t:
            result = run(Path(t), fake_cycle, allow_network=False, sleep_enabled=False)
            self.assertEqual(result["cycle_count"], 0)
            self.assertEqual(result["actual_live_orders_submitted"], 0)

    def test_enabled_one_cycle(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            policy = load(root)
            policy["session_runner_enabled"] = True
            policy["maximum_cycles_per_session"] = 1
            from autonomous_paper_session.io import write_json
            from autonomous_paper_session.config import path
            write_json(path(root), policy)
            result = run(root, fake_cycle, allow_network=False, sleep_enabled=False)
            self.assertEqual(result["cycle_count"], 0)
            self.assertIn("NETWORK_NOT_AUTHORIZED_FOR_SESSION", result["blocking_reasons"])

if __name__ == "__main__":
    unittest.main()
