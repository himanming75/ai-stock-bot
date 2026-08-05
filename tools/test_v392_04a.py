from __future__ import annotations
import unittest

from execution_authorization.dispatch_queue import (
    enqueue_dispatch,
    validate_queue_state,
)
from execution_authorization.dispatch_queue_guard import (
    run_dispatch_queue_gate,
)


def empty_queue():
    return {
        "queue_version": "V392.04A",
        "entries": [],
        "lock": {
            "locked": False,
            "owner": "",
            "locked_at": None,
        },
    }


def preparation():
    return {
        "stage": "V392.03A",
        "state": "DISPATCH_PREPARATION_GATE_READY",
        "status": "PASS",
        "dispatch_preparation_approved": True,
        "queue_entry_allowed": True,
        "dispatch_execution_allowed": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "evaluation": {
            "dispatch_id": "dispatch-001",
            "token_id": "token-001",
            "proposal_id": "proposal-001",
            "order_payload_hash": "payload-hash",
            "policy_hash": "policy-hash",
        },
    }


class Tests(unittest.TestCase):
    def test_empty_queue_valid(self):
        result = validate_queue_state(empty_queue())
        self.assertTrue(result["valid"])

    def test_enqueue(self):
        result = enqueue_dispatch(empty_queue(), preparation(), "owner")
        self.assertTrue(result["approved"])
        self.assertEqual(result["entry"]["sequence"], 1)

    def test_duplicate_rejected(self):
        queue = empty_queue()
        first = enqueue_dispatch(queue, preparation(), "owner")
        second = enqueue_dispatch(first["queue_state"], preparation(), "owner")
        self.assertFalse(second["approved"])

    def test_locked_queue_rejected(self):
        queue = empty_queue()
        queue["lock"] = {
            "locked": True,
            "owner": "other",
            "locked_at": "2029-01-01T00:00:00+00:00",
        }
        result = enqueue_dispatch(queue, preparation(), "owner")
        self.assertFalse(result["approved"])

    def test_invalid_sequence_rejected(self):
        queue = empty_queue()
        queue["entries"] = [{
            "dispatch_id": "d1",
            "token_id": "t1",
            "proposal_id": "p1",
            "sequence": 0,
            "status": "QUEUED",
        }]
        result = enqueue_dispatch(queue, preparation(), "owner")
        self.assertFalse(result["approved"])

    def test_preparation_not_ready(self):
        value = preparation()
        value["state"] = "DISPATCH_PREPARATION_GATE_BLOCKED"
        result = enqueue_dispatch(empty_queue(), value, "owner")
        self.assertFalse(result["approved"])

    def test_fifo_sequence(self):
        queue = empty_queue()
        first = enqueue_dispatch(queue, preparation(), "owner")
        value = preparation()
        value["evaluation"] = dict(value["evaluation"])
        value["evaluation"]["dispatch_id"] = "dispatch-002"
        second = enqueue_dispatch(first["queue_state"], value, "owner")
        self.assertEqual(second["entry"]["sequence"], 2)

    def test_zero_orders(self):
        result = run_dispatch_queue_gate(empty_queue(), preparation(), "owner")
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
