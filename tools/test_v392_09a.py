from __future__ import annotations
import unittest

from execution_authorization.dispatch_context import (
    build_dispatch_context,
)
from execution_authorization.dispatch_context_guard import (
    run_dispatch_engine_preparation,
)


HASH = "a" * 64


def release_gate_result():
    return {
        "stage": "V392.08A",
        "state": "LOCAL_DISPATCH_RELEASE_GATE_READY",
        "status": "PASS",
        "local_dispatch_release_approved": True,
        "local_dispatch_engine_preparation_allowed": True,
        "evaluation": {
            "release_record_hash": HASH,
            "release_record": {
                "dispatch_id": "dispatch-001",
                "proposal_id": "proposal-001",
                "token_id": "token-001",
                "release_token_id": "release-token-001",
                "policy_hash": HASH,
                "order_payload_hash": HASH,
                "target_environment": "PAPER",
            },
        },
    }


def preparation_result():
    payload = {
        "proposal_id": "proposal-001",
        "symbol": "AAPL",
        "side": "BUY",
        "order_type": "MARKET",
        "estimated_notional": 1000,
        "time_in_force": "day",
        "target_environment": "PAPER",
    }
    from execution_authorization.dispatch_context import canonical_hash
    payload_hash = canonical_hash(payload)
    release = release_gate_result()
    release["evaluation"]["release_record"]["order_payload_hash"] = payload_hash
    return {
        "stage": "V392.03A",
        "status": "PASS",
        "evaluation": {
            "dispatch_id": "dispatch-001",
            "proposal_id": "proposal-001",
            "token_id": "token-001",
            "policy_hash": HASH,
            "order_payload_hash": payload_hash,
            "order_payload": payload,
        },
    }, release


class Tests(unittest.TestCase):
    def test_approved(self):
        prep, release = preparation_result()
        result = build_dispatch_context(release, prep, set())
        self.assertTrue(result["approved"])

    def test_replay_rejected(self):
        prep, release = preparation_result()
        first = build_dispatch_context(release, prep, set())
        second = build_dispatch_context(
            release, prep, {first["context_id"]}
        )
        self.assertTrue(second["replay_detected"])
        self.assertFalse(second["approved"])

    def test_dispatch_mismatch(self):
        prep, release = preparation_result()
        prep["evaluation"]["dispatch_id"] = "other"
        result = build_dispatch_context(release, prep, set())
        self.assertFalse(result["approved"])

    def test_proposal_mismatch(self):
        prep, release = preparation_result()
        prep["evaluation"]["proposal_id"] = "other"
        result = build_dispatch_context(release, prep, set())
        self.assertFalse(result["approved"])

    def test_policy_hash_mismatch(self):
        prep, release = preparation_result()
        prep["evaluation"]["policy_hash"] = "b" * 64
        result = build_dispatch_context(release, prep, set())
        self.assertFalse(result["approved"])

    def test_payload_hash_mismatch(self):
        prep, release = preparation_result()
        prep["evaluation"]["order_payload_hash"] = "b" * 64
        result = build_dispatch_context(release, prep, set())
        self.assertFalse(result["approved"])

    def test_release_gate_blocked(self):
        prep, release = preparation_result()
        release["state"] = "LOCAL_DISPATCH_RELEASE_GATE_BLOCKED"
        release["local_dispatch_release_approved"] = False
        result = build_dispatch_context(release, prep, set())
        self.assertFalse(result["approved"])

    def test_zero_orders(self):
        prep, release = preparation_result()
        result = run_dispatch_engine_preparation(release, prep, set())
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
