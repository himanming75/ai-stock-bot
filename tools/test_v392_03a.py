from __future__ import annotations
import unittest

from execution_authorization.dispatch_preparation import (
    build_order_payload,
    canonical_hash,
    evaluate_dispatch_preparation,
)
from execution_authorization.dispatch_preparation_guard import (
    run_dispatch_preparation,
)


def token_gate_result():
    return {
        "stage": "V392.02A",
        "state": "AUTHORIZATION_TOKEN_GATE_OPEN",
        "status": "PASS",
        "token_gate_allowed": True,
        "dispatch_preparation_allowed": True,
        "token_id": "token-001",
        "authorization_result": {
            "policy_hash": "policy-hash",
        },
    }


def proposal():
    return {
        "proposal_id": "proposal-001",
        "symbol": "AAPL",
        "side": "BUY",
        "order_type": "MARKET",
        "estimated_notional": 1000,
        "time_in_force": "day",
    }


def request():
    value = proposal()
    return {
        "dispatch_id": "dispatch-001",
        "token_id": "token-001",
        "proposal_id": "proposal-001",
        "policy_hash": "policy-hash",
        "order_payload_hash": canonical_hash(build_order_payload(value)),
        "target_environment": "PAPER",
        "broker_submission_enabled": False,
        "automatic_dispatch": False,
    }


class Tests(unittest.TestCase):
    def test_approved(self):
        result = evaluate_dispatch_preparation(
            token_gate_result(), proposal(), request(), set()
        )
        self.assertTrue(result["approved"])

    def test_replay_rejected(self):
        result = evaluate_dispatch_preparation(
            token_gate_result(), proposal(), request(), {"dispatch-001"}
        )
        self.assertTrue(result["replay_detected"])
        self.assertFalse(result["approved"])

    def test_token_mismatch(self):
        value = request()
        value["token_id"] = "wrong"
        result = evaluate_dispatch_preparation(
            token_gate_result(), proposal(), value, set()
        )
        self.assertFalse(result["approved"])

    def test_proposal_mismatch(self):
        value = request()
        value["proposal_id"] = "wrong"
        result = evaluate_dispatch_preparation(
            token_gate_result(), proposal(), value, set()
        )
        self.assertFalse(result["approved"])

    def test_payload_hash_mismatch(self):
        value = request()
        value["order_payload_hash"] = "wrong"
        result = evaluate_dispatch_preparation(
            token_gate_result(), proposal(), value, set()
        )
        self.assertFalse(result["approved"])

    def test_live_target_rejected(self):
        value = request()
        value["target_environment"] = "LIVE"
        result = evaluate_dispatch_preparation(
            token_gate_result(), proposal(), value, set()
        )
        self.assertFalse(result["approved"])

    def test_automatic_dispatch_rejected(self):
        value = request()
        value["automatic_dispatch"] = True
        result = evaluate_dispatch_preparation(
            token_gate_result(), proposal(), value, set()
        )
        self.assertFalse(result["approved"])

    def test_zero_orders(self):
        result = run_dispatch_preparation(
            token_gate_result(), proposal(), request(), set()
        )
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
