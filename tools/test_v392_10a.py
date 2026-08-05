from __future__ import annotations
import unittest

from paper_dispatch_engine.engine import (
    canonical_hash,
    run_local_paper_dispatch,
)
from paper_dispatch_engine.guard import run_local_paper_dispatch_guard


HASH = "a" * 64


def context():
    payload = {
        "proposal_id": "proposal-001",
        "symbol": "AAPL",
        "side": "BUY",
        "order_type": "MARKET",
        "estimated_notional": 1000,
        "time_in_force": "day",
        "target_environment": "PAPER",
    }
    core = {
        "context_version": "V392.09A",
        "dispatch_id": "dispatch-001",
        "proposal_id": "proposal-001",
        "token_id": "token-001",
        "release_token_id": "release-token-001",
        "policy_hash": HASH,
        "order_payload_hash": canonical_hash(payload),
        "release_record_hash": HASH,
        "order_payload": payload,
        "target_environment": "PAPER",
        "broker_adapter": "NONE",
        "dispatch_mode": "LOCAL_PREPARATION_ONLY",
    }
    return {
        **core,
        "context_id": "context-001",
        "context_hash": canonical_hash(core),
        "context_state": "LOCAL_DISPATCH_CONTEXT_READY",
        "created_at": "2029-01-01T00:00:00+00:00",
    }


def preparation_result():
    return {
        "stage": "V392.09A",
        "state": "LOCAL_DISPATCH_ENGINE_PREPARATION_READY",
        "status": "PASS",
        "dispatch_context_created": True,
        "local_paper_dispatch_engine_allowed": True,
        "broker_adapter_enabled": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
    }


class Tests(unittest.TestCase):
    def test_accepted(self):
        result = run_local_paper_dispatch(context(), set())
        self.assertTrue(result["approved"])
        self.assertEqual(
            result["local_order"]["submission_state"],
            "ACCEPTED_FOR_SIMULATION",
        )

    def test_replay_rejected(self):
        result = run_local_paper_dispatch(context(), {"context-001"})
        self.assertTrue(result["replay_detected"])
        self.assertFalse(result["approved"])

    def test_context_hash_mismatch(self):
        value = context()
        value["context_hash"] = "bad"
        result = run_local_paper_dispatch(value, set())
        self.assertFalse(result["approved"])

    def test_payload_hash_mismatch(self):
        value = context()
        value["order_payload_hash"] = "bad"
        result = run_local_paper_dispatch(value, set())
        self.assertFalse(result["approved"])

    def test_live_context_rejected(self):
        value = context()
        value["target_environment"] = "LIVE"
        result = run_local_paper_dispatch(value, set())
        self.assertFalse(result["approved"])

    def test_invalid_side_rejected(self):
        value = context()
        value["order_payload"]["side"] = "HOLD"
        result = run_local_paper_dispatch(value, set())
        self.assertFalse(result["approved"])

    def test_preparation_blocked(self):
        prep = preparation_result()
        prep["state"] = "LOCAL_DISPATCH_ENGINE_PREPARATION_BLOCKED"
        result = run_local_paper_dispatch_guard(prep, context(), set())
        self.assertFalse(result["local_dispatch_accepted"])

    def test_zero_orders(self):
        result = run_local_paper_dispatch_guard(
            preparation_result(),
            context(),
            set(),
        )
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)
        self.assertFalse(result["evaluation"]["broker_network_used"])
        self.assertFalse(result["evaluation"]["broker_submission_attempted"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
