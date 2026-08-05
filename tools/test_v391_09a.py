from __future__ import annotations
from datetime import datetime, timezone
import unittest

from autonomous_risk_governor.manual_resume import (
    REQUIRED_PHRASE,
    evaluate_manual_resume,
)
from autonomous_risk_governor.manual_resume_guard import run_guard


def policy_result():
    return {
        "state": "RISK_POLICY_READY",
        "policy_hash": "a" * 64,
        "validation": {"valid": True},
    }


def cleared_pause():
    return {
        "pause_state": "PAUSED",
        "pause_required": False,
        "status": "PASS",
    }


def inactive_kill_switch():
    return {
        "state": "KILL_SWITCH_GUARD_STANDBY",
        "status": "PASS",
        "evaluation": {"kill_switch_active": False},
    }


def request():
    return {
        "approval_phrase": REQUIRED_PHRASE,
        "requested_by": "operator",
        "reason": "Risk conditions cleared and reviewed.",
        "expires_at": "2030-01-01T00:00:00+00:00",
        "automatic_resume": False,
    }


class Tests(unittest.TestCase):
    def test_approved(self):
        result = evaluate_manual_resume(
            cleared_pause(),
            inactive_kill_switch(),
            request(),
            now=datetime(2029, 1, 1, tzinfo=timezone.utc),
        )
        self.assertTrue(result["approved"])

    def test_phrase_mismatch(self):
        value = request()
        value["approval_phrase"] = "WRONG"
        result = evaluate_manual_resume(
            cleared_pause(),
            inactive_kill_switch(),
            value,
            now=datetime(2029, 1, 1, tzinfo=timezone.utc),
        )
        self.assertFalse(result["approved"])

    def test_expired_request(self):
        value = request()
        value["expires_at"] = "2028-01-01T00:00:00+00:00"
        result = evaluate_manual_resume(
            cleared_pause(),
            inactive_kill_switch(),
            value,
            now=datetime(2029, 1, 1, tzinfo=timezone.utc),
        )
        self.assertFalse(result["approved"])

    def test_pause_not_cleared(self):
        pause = cleared_pause()
        pause["pause_required"] = True
        result = evaluate_manual_resume(
            pause,
            inactive_kill_switch(),
            request(),
            now=datetime(2029, 1, 1, tzinfo=timezone.utc),
        )
        self.assertFalse(result["approved"])

    def test_kill_switch_active(self):
        kill = inactive_kill_switch()
        kill["evaluation"]["kill_switch_active"] = True
        kill["state"] = "KILL_SWITCH_GUARD_BLOCKED"
        result = evaluate_manual_resume(
            cleared_pause(),
            kill,
            request(),
            now=datetime(2029, 1, 1, tzinfo=timezone.utc),
        )
        self.assertFalse(result["approved"])

    def test_automatic_resume_rejected(self):
        value = request()
        value["automatic_resume"] = True
        result = evaluate_manual_resume(
            cleared_pause(),
            inactive_kill_switch(),
            value,
            now=datetime(2029, 1, 1, tzinfo=timezone.utc),
        )
        self.assertFalse(result["approved"])

    def test_guard_approved(self):
        result = run_guard(
            policy_result(),
            cleared_pause(),
            inactive_kill_switch(),
            request(),
        )
        self.assertEqual(result["state"], "MANUAL_RESUME_GUARD_APPROVED")

    def test_zero_orders(self):
        result = run_guard(
            policy_result(),
            cleared_pause(),
            inactive_kill_switch(),
            request(),
        )
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
