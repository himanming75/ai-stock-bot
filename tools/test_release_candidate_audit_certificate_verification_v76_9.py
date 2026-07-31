import unittest

from tools.release_candidate_audit_certificate_verification_v76_9 import (
    VerificationError,
    digest,
    validate_config,
)
from tools.verify_release_candidate_audit_certificate_verification_v76_9 import (
    independently_verify,
)


VALID = {
    "verification_scope": "RELEASE_CANDIDATE_AUDIT_CERTIFICATE_VERIFICATION",
    "offline_only": True,
    "require_git_tracked_clean": True,
    "require_head_matches_origin_main": True,
    "require_v76_8_certificate_pass": True,
    "require_v76_8_self_hash_match": True,
    "require_v76_8_summary_match": True,
    "require_all_v76_8_gates_pass": True,
    "require_zero_trading_side_effects": True,
    "network_allowed": False,
    "broker_connection_allowed": False,
    "order_submission_allowed": False,
    "live_trading_allowed": False,
    "live_approval_allowed": False,
    "expected_framework_commit_sha": "a" * 40,
    "expected_v76_8_audit_certificate_sha256": "b" * 64,
    "expected_v76_8_gate_count": 29,
    "expected_anchors": {
        "v76_7_audit_sha256": "c" * 64,
        "v76_6_manifest_sha256": "d" * 64,
        "v76_6_ledger_sha256": "e" * 64,
        "v76_6_certificate_sha256": "f" * 64,
        "v76_6_release_seal_sha256": "1" * 64,
    },
    "v76_8_output_dir": "release/v76_8/output",
}


class TestV769(unittest.TestCase):
    def test_valid_config(self):
        validate_config(dict(VALID))

    def test_live_approval_rejected(self):
        config = dict(VALID)
        config["live_approval_allowed"] = True
        with self.assertRaises(VerificationError):
            validate_config(config)

    def test_bad_commit_rejected(self):
        config = dict(VALID)
        config["expected_framework_commit_sha"] = "bad"
        with self.assertRaises(VerificationError):
            validate_config(config)

    def test_bad_hash_rejected(self):
        config = dict(VALID)
        config["expected_v76_8_audit_certificate_sha256"] = "x" * 64
        with self.assertRaises(VerificationError):
            validate_config(config)

    def test_wrong_gate_count_rejected(self):
        config = dict(VALID)
        config["expected_v76_8_gate_count"] = 28
        with self.assertRaises(VerificationError):
            validate_config(config)

    def test_digest_deterministic(self):
        self.assertEqual(digest({"b": 2, "a": 1}), digest({"a": 1, "b": 2}))

    def test_independent_verifier_pass(self):
        result = {
            "status": "PASS",
            "audit_certificate_independently_verified": True,
            "verification_result": {
                "gate_count": 2,
                "passed_gate_count": 2,
                "failed_gate_count": 0,
            },
            "source_certificate": {
                "audit_certificate_sha256": "a" * 64,
            },
            "network_allowed": False,
            "orders_submitted": 0,
            "approved_for_live": False,
        }
        result["verification_sha256"] = digest(result)
        summary = {
            "status": "PASS",
            "verification_sha256": result["verification_sha256"],
            "audit_certificate_sha256": "a" * 64,
        }
        verdict = independently_verify(result, summary)
        self.assertEqual(verdict["status"], "PASS")
        self.assertTrue(verdict["verified"])

    def test_independent_verifier_tamper(self):
        result = {
            "status": "PASS",
            "audit_certificate_independently_verified": True,
            "verification_result": {
                "gate_count": 1,
                "passed_gate_count": 1,
                "failed_gate_count": 0,
            },
            "source_certificate": {
                "audit_certificate_sha256": "a" * 64,
            },
            "network_allowed": False,
            "orders_submitted": 0,
            "approved_for_live": False,
        }
        result["verification_sha256"] = digest(result)
        result["orders_submitted"] = 1
        summary = {
            "status": "PASS",
            "verification_sha256": result["verification_sha256"],
            "audit_certificate_sha256": "a" * 64,
        }
        verdict = independently_verify(result, summary)
        self.assertEqual(verdict["status"], "FAIL")
        self.assertGreater(verdict["error_count"], 0)


if __name__ == "__main__":
    unittest.main()
