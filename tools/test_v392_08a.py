from __future__ import annotations
import unittest

from execution_authorization.local_dispatch_release import (
    evaluate_local_dispatch_release,
)
from execution_authorization.local_dispatch_release_guard import (
    run_local_dispatch_release_gate,
)


HASH = "a" * 64


def release_token_result():
    return {
        "stage": "V392.07A",
        "state": "RELEASE_TOKEN_GATE_OPEN",
        "status": "PASS",
        "release_token_gate_allowed": True,
        "local_dispatch_release_allowed": True,
        "evaluation": {
            "dispatch_id": "dispatch-001",
            "proposal_id": "proposal-001",
            "release_token_id": "release-token-001",
            "checks": {
                "queue_hash_matches": True,
                "head_entry_hash_matches": True,
            },
        },
    }


def queue_state():
    return {
        "queue_version": "V392.04A",
        "entries": [{
            "dispatch_id": "dispatch-001",
            "token_id": "token-001",
            "proposal_id": "proposal-001",
            "sequence": 1,
            "status": "QUEUED",
            "queued_at": "2029-01-01T00:00:00+00:00",
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
    def test_approved(self):
        result = evaluate_local_dispatch_release(
            release_token_result(), queue_state(), set()
        )
        self.assertTrue(result["approved"])

    def test_replay_rejected(self):
        result = evaluate_local_dispatch_release(
            release_token_result(), queue_state(), {"dispatch-001"}
        )
        self.assertTrue(result["replay_detected"])
        self.assertFalse(result["approved"])

    def test_dispatch_mismatch(self):
        value = release_token_result()
        value["evaluation"] = dict(value["evaluation"])
        value["evaluation"]["dispatch_id"] = "other"
        result = evaluate_local_dispatch_release(
            value, queue_state(), set()
        )
        self.assertFalse(result["approved"])

    def test_proposal_mismatch(self):
        value = release_token_result()
        value["evaluation"] = dict(value["evaluation"])
        value["evaluation"]["proposal_id"] = "other"
        result = evaluate_local_dispatch_release(
            value, queue_state(), set()
        )
        self.assertFalse(result["approved"])

    def test_locked_queue_rejected(self):
        queue = queue_state()
        queue["lock"] = {
            "locked": True,
            "owner": "worker",
            "locked_at": "2029-01-01T00:00:00+00:00",
        }
        result = evaluate_local_dispatch_release(
            release_token_result(), queue, set()
        )
        self.assertFalse(result["approved"])

    def test_head_not_queued(self):
        queue = queue_state()
        queue["entries"][0]["status"] = "RELEASED"
        result = evaluate_local_dispatch_release(
            release_token_result(), queue, set()
        )
        self.assertFalse(result["approved"])

    def test_release_token_gate_blocked(self):
        value = release_token_result()
        value["state"] = "RELEASE_TOKEN_GATE_BLOCKED"
        value["release_token_gate_allowed"] = False
        result = evaluate_local_dispatch_release(
            value, queue_state(), set()
        )
        self.assertFalse(result["approved"])

    def test_zero_orders(self):
        result = run_local_dispatch_release_gate(
            release_token_result(), queue_state(), set()
        )
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
