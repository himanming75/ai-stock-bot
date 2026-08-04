import json
import tempfile
import unittest
from pathlib import Path

from autonomous_cycle.identity import build_cycle_identity
from autonomous_cycle.dedup import detect_duplicate
from autonomous_cycle.lock import acquire_lock, release_lock
from autonomous_cycle.retry import can_retry
from autonomous_cycle.executor import execute_step
from autonomous_cycle.state import resolve_cycle_state
from autonomous_cycle.engine import evaluate

class Tests(unittest.TestCase):
    def test_identity_stable(self):
        decision = {
            "decision_id": "abc",
            "autonomous_decision": {"decision": "ACT"},
        }
        policy = {"policy_version": "V103.01"}
        a = build_cycle_identity(decision, policy, "2026-08-04")
        b = build_cycle_identity(decision, policy, "2026-08-04")
        self.assertEqual(a["cycle_key"], b["cycle_key"])

    def test_duplicate(self):
        value = detect_duplicate(
            "key",
            [{"cycle_key": "key", "state": "AUTONOMOUS_CYCLE_HOLD"}],
        )
        self.assertTrue(value["duplicate_cycle"])

    def test_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "lock.json"
            acquired = acquire_lock(path, "cycle-1", 30)
            self.assertTrue(acquired["acquired"])
            self.assertTrue(release_lock(path, "cycle-1")["released"])

    def test_retry(self):
        value = can_retry(1, {"maximum_step_attempts": 3})
        self.assertTrue(value["retry_allowed"])

    def test_step(self):
        step = {
            "step_number": 1,
            "step_id": "VALIDATE_SOURCE_DECISION",
            "state": "PENDING",
            "attempt_count": 0,
            "error": None,
        }
        result = execute_step(
            step,
            {"source_status": "PASS"},
            {"maximum_step_attempts": 3},
        )
        self.assertEqual(result["state"], "COMPLETED")

    def test_act_waits_for_approval(self):
        value = resolve_cycle_state({
            "autonomous_decision": {"decision": "ACT"},
            "approval_gate": {"approval_eligible": True},
        })
        self.assertEqual(
            value["state"],
            "AUTONOMOUS_CYCLE_WAITING_FOR_MANUAL_APPROVAL",
        )
        self.assertFalse(value["approval_granted"])

    def test_hold(self):
        value = resolve_cycle_state({
            "autonomous_decision": {"decision": "HOLD"},
            "approval_gate": {},
        })
        self.assertEqual(value["state"], "AUTONOMOUS_CYCLE_HOLD")

    def test_missing_source_blocks(self):
        with tempfile.TemporaryDirectory() as temp:
            result = evaluate(Path(temp), "2026-08-04")
            self.assertEqual(result["state"], "AUTONOMOUS_CYCLE_BLOCKED")

    def test_orders_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            result = evaluate(Path(temp), "2026-08-04")
            self.assertEqual(result["actual_orders_submitted"], 0)

    def test_duplicate_second_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = (
                root / "release/v102_33_to_v102_64/actual/"
                "autonomous_decision_result.json"
            )
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(json.dumps({
                "status": "PASS",
                "decision_id": "d1",
                "state": "AUTONOMOUS_DECISION_HOLD",
                "autonomous_decision": {"decision": "HOLD"},
                "approval_gate": {"approval_eligible": False},
            }), encoding="utf-8")
            policy = (
                root / "release/v103_01_to_v103_32/input/"
                "autonomous_cycle_policy.json"
            )
            policy.parent.mkdir(parents=True, exist_ok=True)
            policy.write_text(json.dumps({
                "policy_version": "V103.01",
                "checkpoint_enabled": True,
                "lock_timeout_seconds": 30,
                "maximum_step_attempts": 3,
            }), encoding="utf-8")
            first = evaluate(root, "2026-08-04")
            second = evaluate(root, "2026-08-04")
            self.assertEqual(first["state"], "AUTONOMOUS_CYCLE_HOLD")
            self.assertEqual(
                second["state"],
                "AUTONOMOUS_CYCLE_DUPLICATE_BLOCKED",
            )

if __name__ == "__main__":
    unittest.main()
