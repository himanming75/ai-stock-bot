import unittest

from tools.verify_local_trigger_dispatcher_v83_29_to_v83_32 import (
    evaluate_verification,
)


def base_result():
    return {
        "stage_range": "V83.29-V83.32",
        "state": "LOCAL_TRIGGER_DISPATCH_WAIT_TRIGGER",
        "status": "PASS",
        "issues": [],
        "paper_only": True,
        "broker_write_enabled": False,
        "order_submission_enabled": False,
        "live_trading_enabled": False,
        "actual_external_network_used": False,
        "network_requests_executed": 0,
        "write_requests_executed": 0,
        "actual_paper_orders_submitted": 0,
        "live_orders_submitted": 0,
    }


class VerifyHotfixTests(unittest.TestCase):
    def test_wait_trigger_passes(self):
        result = evaluate_verification(base_result())
        self.assertEqual(result["verification_status"], "PASS")
        self.assertEqual(result["accepted_as"], "EXPECTED_WAIT_STATE")

    def test_missing_trigger_plan_safe_mode_passes(self):
        payload = base_result()
        payload.update({
            "state": "LOCAL_TRIGGER_DISPATCH_SAFE_MODE",
            "status": "BLOCKED",
            "issues": [{
                "blocking": True,
                "code": "TRIGGER_PLAN_NOT_FOUND",
                "detail": "plan missing",
            }],
        })
        result = evaluate_verification(payload)
        self.assertEqual(result["verification_status"], "PASS")
        self.assertEqual(result["accepted_as"], "EXPECTED_TRIGGER_ABSENCE")

    def test_disallowed_command_still_fails(self):
        payload = base_result()
        payload.update({
            "state": "LOCAL_TRIGGER_DISPATCH_SAFE_MODE",
            "status": "BLOCKED",
            "issues": [{
                "blocking": True,
                "code": "DISALLOWED_TARGET_SCRIPT",
                "detail": "evil.ps1",
            }],
        })
        result = evaluate_verification(payload)
        self.assertEqual(result["verification_status"], "FAIL")

    def test_nonzero_orders_still_fail(self):
        payload = base_result()
        payload["actual_paper_orders_submitted"] = 1
        result = evaluate_verification(payload)
        self.assertEqual(result["verification_status"], "FAIL")
        self.assertIn("paper_orders_zero", result["failed"])


if __name__ == "__main__":
    unittest.main()
