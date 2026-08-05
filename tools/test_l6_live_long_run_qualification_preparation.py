from pathlib import Path
import tempfile
import unittest

from live_qualification.audits import (
    crash_resume_audit,
    kill_switch_response_audit,
)
from live_qualification.fault_matrix import run_fault_matrix
from live_qualification.policy import LiveLongRunPolicy


class Tests(unittest.TestCase):
    def test_policy(self):
        result = LiveLongRunPolicy(
            required_cycles=3,
            maximum_failed_cycles=0,
            maximum_heartbeat_gap_seconds=300,
            require_zero_duplicate_cycles=True,
            require_zero_unresolved_drift=True,
            require_kill_switch_response=True,
            require_crash_resume_test=True,
            fail_closed=True,
        ).evaluate()
        self.assertTrue(result["valid"])

    def test_fault_matrix(self):
        result = run_fault_matrix()
        self.assertTrue(result["passed"])
        self.assertEqual(result["failed_count"], 0)

    def test_kill_switch_response_blocks_orders(self):
        result = kill_switch_response_audit()
        self.assertFalse(result["live_order_submission_allowed"])
        self.assertTrue(result["passed"])

    def test_crash_resume_manual(self):
        result = crash_resume_audit()
        self.assertTrue(result["passed"])
        self.assertTrue(
            result["checks"]["operator_review_required"]
        )

    def test_zero_order_design(self):
        result = run_fault_matrix()
        self.assertTrue(all(
            item["live_order_submission_allowed"] is False
            for item in result["results"]
        ))


if __name__ == "__main__":
    unittest.main(verbosity=2)
