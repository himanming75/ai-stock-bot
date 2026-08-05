from __future__ import annotations
from datetime import datetime, timezone, timedelta
import unittest

from execution_authorization.release_token import (
    create_release_token,
    validate_release_token,
)
from execution_authorization.release_token_guard import run_release_token_gate


SECRET = "test-secret"
NOW = datetime(2029, 1, 1, tzinfo=timezone.utc)
HASH = "a" * 64


def release_result():
    return {
        "stage": "V392.06A",
        "state": "QUEUE_RELEASE_AUTHORIZATION_READY",
        "status": "PASS",
        "queue_release_authorized": True,
        "release_token_preparation_allowed": True,
        "evaluation": {
            "release_id": "release-001",
            "dispatch_id": "dispatch-001",
            "token_id": "token-001",
            "proposal_id": "proposal-001",
            "queue_hash": HASH,
            "head_entry_hash": HASH,
        },
    }


def release_token():
    return create_release_token(
        release_result=release_result(),
        secret=SECRET,
        issued_at=NOW.isoformat(),
        expires_at=(NOW + timedelta(minutes=5)).isoformat(),
        nonce="nonce-001",
    )


class Tests(unittest.TestCase):
    def test_valid_release_token(self):
        result = validate_release_token(
            release_token(), release_result(), SECRET, set(), NOW
        )
        self.assertTrue(result["approved"])

    def test_bad_signature(self):
        value = release_token()
        value["signature"] = "bad"
        result = validate_release_token(
            value, release_result(), SECRET, set(), NOW
        )
        self.assertFalse(result["approved"])

    def test_expired(self):
        value = create_release_token(
            release_result=release_result(),
            secret=SECRET,
            issued_at=(NOW - timedelta(minutes=10)).isoformat(),
            expires_at=(NOW - timedelta(minutes=5)).isoformat(),
            nonce="nonce-expired",
        )
        result = validate_release_token(
            value, release_result(), SECRET, set(), NOW
        )
        self.assertFalse(result["approved"])

    def test_replay_rejected(self):
        value = release_token()
        result = validate_release_token(
            value,
            release_result(),
            SECRET,
            {value["release_token_id"]},
            NOW,
        )
        self.assertTrue(result["replay_detected"])
        self.assertFalse(result["approved"])

    def test_release_id_mismatch(self):
        result_value = release_result()
        result_value["evaluation"] = dict(result_value["evaluation"])
        result_value["evaluation"]["release_id"] = "other"
        result = validate_release_token(
            release_token(), result_value, SECRET, set(), NOW
        )
        self.assertFalse(result["approved"])

    def test_queue_hash_mismatch(self):
        result_value = release_result()
        result_value["evaluation"] = dict(result_value["evaluation"])
        result_value["evaluation"]["queue_hash"] = "b" * 64
        result = validate_release_token(
            release_token(), result_value, SECRET, set(), NOW
        )
        self.assertFalse(result["approved"])

    def test_release_not_authorized(self):
        result_value = release_result()
        result_value["queue_release_authorized"] = False
        result = validate_release_token(
            release_token(), result_value, SECRET, set(), NOW
        )
        self.assertFalse(result["approved"])

    def test_zero_orders(self):
        value = release_token()
        result = run_release_token_gate(
            release_result(), value, SECRET, set()
        )
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
