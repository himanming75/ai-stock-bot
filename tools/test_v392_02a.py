from __future__ import annotations
from datetime import datetime, timezone, timedelta
import unittest

from execution_authorization.token_gate import create_token, validate_token
from execution_authorization.token_gate_runner import run_token_gate


SECRET = "test-secret"
NOW = datetime(2029, 1, 1, tzinfo=timezone.utc)


def authorization_result():
    return {
        "stage": "V392.01A",
        "state": "EXECUTION_AUTHORIZATION_APPROVED",
        "status": "PASS",
        "authorization_approved": True,
        "execution_authorization_allowed": True,
        "proposal_id": "proposal-001",
        "proposal_hash": "proposal-hash",
        "policy_hash": "policy-hash",
    }


def proposal():
    return {
        "proposal_id": "proposal-001",
        "symbol": "AAPL",
        "side": "BUY",
    }


def token():
    return create_token(
        authorization_result(),
        proposal(),
        SECRET,
        NOW.isoformat(),
        (NOW + timedelta(minutes=5)).isoformat(),
        "nonce-001",
    )


class Tests(unittest.TestCase):
    def test_valid_token(self):
        result = validate_token(
            token(), authorization_result(), proposal(), SECRET, set(), NOW
        )
        self.assertTrue(result["approved"])

    def test_bad_signature(self):
        value = token()
        value["signature"] = "bad"
        result = validate_token(
            value, authorization_result(), proposal(), SECRET, set(), NOW
        )
        self.assertFalse(result["approved"])

    def test_expired(self):
        value = create_token(
            authorization_result(),
            proposal(),
            SECRET,
            (NOW - timedelta(minutes=10)).isoformat(),
            (NOW - timedelta(minutes=5)).isoformat(),
            "nonce-expired",
        )
        result = validate_token(
            value, authorization_result(), proposal(), SECRET, set(), NOW
        )
        self.assertFalse(result["approved"])

    def test_replay_rejected(self):
        value = token()
        result = validate_token(
            value,
            authorization_result(),
            proposal(),
            SECRET,
            {value["token_id"]},
            NOW,
        )
        self.assertTrue(result["replay_detected"])
        self.assertFalse(result["approved"])

    def test_proposal_id_mismatch(self):
        value = proposal()
        value["proposal_id"] = "other"
        result = validate_token(
            token(), authorization_result(), value, SECRET, set(), NOW
        )
        self.assertFalse(result["approved"])

    def test_symbol_mismatch(self):
        value = proposal()
        value["symbol"] = "MSFT"
        result = validate_token(
            token(), authorization_result(), value, SECRET, set(), NOW
        )
        self.assertFalse(result["approved"])

    def test_authorization_blocked(self):
        auth = authorization_result()
        auth["authorization_approved"] = False
        result = validate_token(
            token(), auth, proposal(), SECRET, set(), NOW
        )
        self.assertFalse(result["approved"])

    def test_zero_orders(self):
        value = token()
        result = run_token_gate(
            authorization_result(),
            proposal(),
            value,
            SECRET,
            set(),
        )
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
