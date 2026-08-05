from __future__ import annotations
from datetime import datetime, timezone
import unittest

from execution_authorization.authorization_guard import (
    REQUIRED_APPROVAL_PHRASE,
    run_authorization,
)
from execution_authorization.token import canonical_hash


def policy():
    return {
        "stage": "V392.01A",
        "mode": "EXECUTION_AUTHORIZATION_FOUNDATION",
        "authorization_required": True,
        "paper_endpoint_only": True,
        "live_submission_enabled": False,
        "broker_write_enabled": False,
        "manual_approval_required": True,
        "automatic_authorization_enabled": False,
        "authorization_token_ttl_seconds": 300,
    }


def risk():
    return {
        "stage": "V391.10A",
        "status": "PASS",
        "risk_governor_decision": "ALLOW",
        "risk_operations_allowed": True,
        "policy_hash": "a" * 64,
    }


def proposal():
    return {
        "proposal_id": "proposal-001",
        "symbol": "AAPL",
        "side": "BUY",
        "estimated_notional": 1000,
    }


def request():
    value = proposal()
    return {
        "proposal_id": value["proposal_id"],
        "proposal_hash": canonical_hash(value),
        "policy_hash": "a" * 64,
        "approval_phrase": REQUIRED_APPROVAL_PHRASE,
        "approved_by": "operator",
        "reason": "Reviewed for paper authorization.",
        "expires_at": "2030-01-01T00:00:00+00:00",
        "target_environment": "PAPER",
        "automatic_authorization": False,
    }


class Tests(unittest.TestCase):
    def test_approved(self):
        result = run_authorization(
            policy(), risk(), proposal(), request(),
            now=datetime(2029, 1, 1, tzinfo=timezone.utc),
        )
        self.assertTrue(result["authorization_approved"])

    def test_risk_blocked(self):
        value = risk()
        value["risk_governor_decision"] = "BLOCKED"
        result = run_authorization(
            policy(), value, proposal(), request(),
            now=datetime(2029, 1, 1, tzinfo=timezone.utc),
        )
        self.assertFalse(result["authorization_approved"])

    def test_proposal_hash_mismatch(self):
        value = request()
        value["proposal_hash"] = "wrong"
        result = run_authorization(
            policy(), risk(), proposal(), value,
            now=datetime(2029, 1, 1, tzinfo=timezone.utc),
        )
        self.assertFalse(result["authorization_approved"])

    def test_policy_hash_mismatch(self):
        value = request()
        value["policy_hash"] = "b" * 64
        result = run_authorization(
            policy(), risk(), proposal(), value,
            now=datetime(2029, 1, 1, tzinfo=timezone.utc),
        )
        self.assertFalse(result["authorization_approved"])

    def test_expired(self):
        value = request()
        value["expires_at"] = "2028-01-01T00:00:00+00:00"
        result = run_authorization(
            policy(), risk(), proposal(), value,
            now=datetime(2029, 1, 1, tzinfo=timezone.utc),
        )
        self.assertFalse(result["authorization_approved"])

    def test_live_target_rejected(self):
        value = request()
        value["target_environment"] = "LIVE"
        result = run_authorization(
            policy(), risk(), proposal(), value,
            now=datetime(2029, 1, 1, tzinfo=timezone.utc),
        )
        self.assertFalse(result["authorization_approved"])

    def test_automatic_authorization_rejected(self):
        value = request()
        value["automatic_authorization"] = True
        result = run_authorization(
            policy(), risk(), proposal(), value,
            now=datetime(2029, 1, 1, tzinfo=timezone.utc),
        )
        self.assertFalse(result["authorization_approved"])

    def test_zero_orders(self):
        result = run_authorization(
            policy(), risk(), proposal(), request(),
            now=datetime(2029, 1, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
