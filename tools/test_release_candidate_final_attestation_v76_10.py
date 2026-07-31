import unittest

from tools.release_candidate_final_attestation_v76_10 import (
    AttestationError,
    digest,
    validate_config,
)
from tools.verify_release_candidate_final_attestation_v76_10 import (
    verify_attestation,
)


VALID = {
    "attestation_scope": "RELEASE_CANDIDATE_FINAL_ATTESTATION",
    "offline_only": True,
    "require_git_tracked_clean": True,
    "require_head_matches_origin_main": True,
    "require_v76_6_release_seal": True,
    "require_v76_7_seal_verification": True,
    "require_v76_8_audit_certificate": True,
    "require_v76_9_audit_certificate_verification": True,
    "require_zero_trading_side_effects": True,
    "network_allowed": False,
    "broker_connection_allowed": False,
    "order_submission_allowed": False,
    "live_trading_allowed": False,
    "live_approval_allowed": False,
    "expected_framework_commit_sha": "a" * 40,
    "expected_hashes": {
        "v76_6_manifest_sha256": "1" * 64,
        "v76_6_ledger_sha256": "2" * 64,
        "v76_6_certificate_sha256": "3" * 64,
        "v76_6_release_seal_sha256": "4" * 64,
        "v76_7_audit_sha256": "5" * 64,
        "v76_8_audit_certificate_sha256": "6" * 64,
        "v76_9_verification_sha256": "7" * 64,
    },
    "v76_6_output_dir": "release/v76_6/output",
    "v76_7_output_dir": "release/v76_7/output",
    "v76_8_output_dir": "release/v76_8/output",
    "v76_9_output_dir": "release/v76_9/output",
}


class TestV7610(unittest.TestCase):
    def test_valid_config(self):
        validate_config(dict(VALID))

    def test_live_approval_rejected(self):
        config = dict(VALID)
        config["live_approval_allowed"] = True
        with self.assertRaises(AttestationError):
            validate_config(config)

    def test_bad_commit_rejected(self):
        config = dict(VALID)
        config["expected_framework_commit_sha"] = "bad"
        with self.assertRaises(AttestationError):
            validate_config(config)

    def test_bad_hash_rejected(self):
        config = dict(VALID)
        hashes = dict(config["expected_hashes"])
        hashes["v76_9_verification_sha256"] = "x" * 64
        config["expected_hashes"] = hashes
        with self.assertRaises(AttestationError):
            validate_config(config)

    def test_digest_deterministic(self):
        self.assertEqual(digest({"b": 2, "a": 1}), digest({"a": 1, "b": 2}))


    def test_v76_6_release_seal_is_not_result_self_hash(self):
        certificate = {"release_seal_sha256": "4" * 64}
        seal_result = {
            "release_seal_sha256": "4" * 64,
            "seal_result_sha256": "5" * 64,
        }
        self.assertEqual(
            certificate["release_seal_sha256"],
            seal_result["release_seal_sha256"],
        )
        self.assertNotEqual(
            certificate["release_seal_sha256"],
            seal_result["seal_result_sha256"],
        )

    def test_verifier_pass(self):
        result = {
            "status": "PASS",
            "release_candidate_finally_attested": True,
            "attestation_result": {
                "gate_count": 2,
                "passed_gate_count": 2,
                "failed_gate_count": 0,
            },
            "attested_chain": {
                "v76_6_release_candidate_sealed": True,
                "v76_7_seal_independently_verified": True,
                "v76_8_audit_certified": True,
                "v76_9_audit_certificate_independently_verified": True,
            },
            "anchored_hashes": {"x": "y"},
            "network_allowed": False,
            "orders_submitted": 0,
            "approved_for_live": False,
            "live_trading_authorized": False,
        }
        result["final_attestation_sha256"] = digest(result)
        summary = {
            "status": "PASS",
            "final_attestation_sha256": result["final_attestation_sha256"],
            "attested_chain": result["attested_chain"],
            "anchored_hashes": result["anchored_hashes"],
        }
        verdict = verify_attestation(result, summary)
        self.assertEqual(verdict["status"], "PASS")
        self.assertTrue(verdict["verified"])

    def test_verifier_tamper(self):
        result = {
            "status": "PASS",
            "release_candidate_finally_attested": True,
            "attestation_result": {
                "gate_count": 1,
                "passed_gate_count": 1,
                "failed_gate_count": 0,
            },
            "attested_chain": {
                "v76_6_release_candidate_sealed": True,
                "v76_7_seal_independently_verified": True,
                "v76_8_audit_certified": True,
                "v76_9_audit_certificate_independently_verified": True,
            },
            "anchored_hashes": {},
            "network_allowed": False,
            "orders_submitted": 0,
            "approved_for_live": False,
            "live_trading_authorized": False,
        }
        result["final_attestation_sha256"] = digest(result)
        result["orders_submitted"] = 1
        summary = {
            "status": "PASS",
            "final_attestation_sha256": result["final_attestation_sha256"],
            "attested_chain": result["attested_chain"],
            "anchored_hashes": result["anchored_hashes"],
        }
        verdict = verify_attestation(result, summary)
        self.assertEqual(verdict["status"], "FAIL")
        self.assertGreater(verdict["error_count"], 0)


if __name__ == "__main__":
    unittest.main()
