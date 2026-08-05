from __future__ import annotations
from datetime import datetime, timezone, timedelta
import unittest

from execution_authorization.queue_inspection import inspect_queue
from execution_authorization.queue_inspection_guard import (
    run_queue_inspection_gate,
)


NOW = datetime(2029, 1, 1, tzinfo=timezone.utc)
HASH = "a" * 64


def queue_state():
    return {
        "queue_version": "V392.04A",
        "entries": [{
            "dispatch_id": "dispatch-001",
            "token_id": "token-001",
            "proposal_id": "proposal-001",
            "sequence": 1,
            "status": "QUEUED",
            "queued_at": (NOW - timedelta(minutes=1)).isoformat(),
            "order_payload_hash": HASH,
            "policy_hash": HASH,
            "target_environment": "PAPER",
        }],
        "lock": {
            "locked": False,
            "owner": "",
            "locked_at": None,
        },
    }


class Tests(unittest.TestCase):
    def test_ready(self):
        result = inspect_queue(queue_state(), 900, NOW)
        self.assertTrue(result["release_ready"])
        self.assertEqual(result["state"], "QUEUE_INSPECTION_READY")

    def test_empty_queue(self):
        value = queue_state()
        value["entries"] = []
        result = inspect_queue(value, 900, NOW)
        self.assertFalse(result["release_ready"])

    def test_locked_queue(self):
        value = queue_state()
        value["lock"] = {
            "locked": True,
            "owner": "worker",
            "locked_at": NOW.isoformat(),
        }
        result = inspect_queue(value, 900, NOW)
        self.assertEqual(result["state"], "QUEUE_INSPECTION_LOCKED")

    def test_stale_entry(self):
        value = queue_state()
        value["entries"][0]["queued_at"] = (
            NOW - timedelta(hours=1)
        ).isoformat()
        result = inspect_queue(value, 900, NOW)
        self.assertEqual(result["stale_entry_count"], 1)
        self.assertFalse(result["release_ready"])

    def test_duplicate_dispatch(self):
        value = queue_state()
        second = dict(value["entries"][0])
        second["sequence"] = 2
        value["entries"].append(second)
        result = inspect_queue(value, 900, NOW)
        self.assertFalse(result["valid"])

    def test_sequence_gap(self):
        value = queue_state()
        value["entries"][0]["sequence"] = 2
        result = inspect_queue(value, 900, NOW)
        self.assertIn("FIFO_SEQUENCE_GAP", result["errors"])

    def test_invalid_payload_hash(self):
        value = queue_state()
        value["entries"][0]["order_payload_hash"] = "bad"
        result = inspect_queue(value, 900, NOW)
        self.assertFalse(result["valid"])

    def test_zero_orders(self):
        value = queue_state()
        value["entries"][0]["queued_at"] = datetime.now(timezone.utc).isoformat()
        result = run_queue_inspection_gate(value, 900)
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
