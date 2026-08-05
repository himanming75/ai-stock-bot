from __future__ import annotations
from datetime import datetime, timezone, timedelta
import unittest

from execution_authorization.queue_release import (
    REQUIRED_APPROVAL_PHRASE,
    canonical_hash,
    evaluate_queue_release,
)
from execution_authorization.queue_release_guard import (
    run_queue_release_authorization,
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
            "queued_at": NOW.isoformat(),
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


def inspection():
    queue = queue_state()
    head = queue["entries"][0]
    return {
        "stage": "V392.05A",
        "state": "QUEUE_INSPECTION_GATE_READY",
        "status": "PASS",
        "queue_release_inspection_passed": True,
        "release_authorization_allowed": True,
        "evaluation": {
            "queue_hash": canonical_hash(queue),
            "head_entry": {
                "dispatch_id": head["dispatch_id"],
                "entry_hash": canonical_hash(head),
                "sequence": 1,
                "status": "QUEUED",
                "valid": True,
            },
        },
    }


def request():
    queue = queue_state()
    head = queue["entries"][0]
    return {
        "release_id": "release-001",
        "dispatch_id": "dispatch-001",
        "token_id": "token-001",
        "proposal_id": "proposal-001",
        "queue_hash": canonical_hash(queue),
        "head_entry_hash": canonical_hash(head),
        "approval_phrase": REQUIRED_APPROVAL_PHRASE,
        "approved_by": "operator",
        "reason": "Reviewed FIFO head.",
        "expires_at": (NOW + timedelta(minutes=5)).isoformat(),
        "target_environment": "PAPER",
        "automatic_release": False,
        "dispatch_execution_enabled": False,
    }


class Tests(unittest.TestCase):
    def test_approved(self):
        result = evaluate_queue_release(
            inspection(), queue_state(), request(), set(), NOW
        )
        self.assertTrue(result["approved"])

    def test_non_head_dispatch_rejected(self):
        value = request()
        value["dispatch_id"] = "other"
        result = evaluate_queue_release(
            inspection(), queue_state(), value, set(), NOW
        )
        self.assertFalse(result["approved"])

    def test_queue_hash_mismatch(self):
        value = request()
        value["queue_hash"] = "bad"
        result = evaluate_queue_release(
            inspection(), queue_state(), value, set(), NOW
        )
        self.assertFalse(result["approved"])

    def test_head_hash_mismatch(self):
        value = request()
        value["head_entry_hash"] = "bad"
        result = evaluate_queue_release(
            inspection(), queue_state(), value, set(), NOW
        )
        self.assertFalse(result["approved"])

    def test_locked_queue_rejected(self):
        queue = queue_state()
        queue["lock"] = {
            "locked": True,
            "owner": "worker",
            "locked_at": NOW.isoformat(),
        }
        result = evaluate_queue_release(
            inspection(), queue, request(), set(), NOW
        )
        self.assertFalse(result["approved"])

    def test_expired_rejected(self):
        value = request()
        value["expires_at"] = (NOW - timedelta(seconds=1)).isoformat()
        result = evaluate_queue_release(
            inspection(), queue_state(), value, set(), NOW
        )
        self.assertFalse(result["approved"])

    def test_replay_rejected(self):
        result = evaluate_queue_release(
            inspection(), queue_state(), request(), {"release-001"}, NOW
        )
        self.assertTrue(result["replay_detected"])
        self.assertFalse(result["approved"])

    def test_zero_orders(self):
        result = run_queue_release_authorization(
            inspection(), queue_state(), request(), set()
        )
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
