import unittest

from tools.release_candidate_audit_certificate_v76_8 import (
    CertificateError,
    digest,
    internal_hash_valid,
    validate_config,
)
from tools.verify_release_candidate_audit_certificate_v76_8 import (
    verify_certificate,
)


VALID = {
    "certificate_scope": "RELEASE_CANDIDATE_AUDIT_CERTIFICATE",
    "offline_only": True,
    "require_git_tracked_clean": True,
    "require_head_matches_origin_main": True,
    "require_v76_7_audit_pass": True,
    "require_all_anchored_hashes_match": True,
    "require_zero_trading_side_effects": True,
    "network_allowed": False,
    "broker_connection_allowed": False,
    "order_submission_allowed": False,
    "live_trading_allowed": False,
    "live_approval_allowed": False,
    "expected_framework_commit_sha": "a" * 40,
    "expected_v76_6_sealed_commit_sha": "b" * 40,
    "expected_hashes": {
        "v76_7_audit_sha256": "c" * 64,
        "v76_6_manifest_sha256": "d" * 64,
        "v76_6_ledger_sha256": "e" * 64,
        "v76_6_certificate_sha256": "f" * 64,
        "v76_6_release_seal_sha256": "1" * 64,
    },
    "v76_7_output_dir": "release/v76_7/output",
    "v76_6_output_dir": "release/v76_6/output",
}


class TestReleaseCandidateAuditCertificateV768(unittest.TestCase):
    def test_valid_config(self):
        validate_config(dict(VALID))

    def test_live_approval_rejected(self):
        config = dict(VALID)
        config["live_approval_allowed"] = True
        with self.assertRaises(CertificateError):
            validate_config(config)

    def test_bad_framework_commit_rejected(self):
        config = dict(VALID)
        config["expected_framework_commit_sha"] = "bad"
        with self.assertRaises(CertificateError):
            validate_config(config)

    def test_bad_hash_rejected(self):
        config = dict(VALID)
        config["expected_hashes"] = dict(VALID["expected_hashes"])
        config["expected_hashes"]["v76_7_audit_sha256"] = "x" * 64
        with self.assertRaises(CertificateError):
            validate_config(config)

    def test_internal_hash_valid(self):
        value = {"status": "PASS"}
        value["hash"] = digest(value)
        valid, stored, calculated = internal_hash_valid(value, "hash")
        self.assertTrue(valid)
        self.assertEqual(stored, calculated)

    def test_internal_hash_tamper(self):
        value = {"status": "PASS"}
        value["hash"] = digest(value)
        value["status"] = "FAIL"
        valid, _, _ = internal_hash_valid(value, "hash")
        self.assertFalse(valid)

    def test_certificate_verifier_pass(self):
        certificate = {
            "status": "PASS",
            "release_candidate_audit_certified": True,
            "network_allowed": False,
            "orders_submitted": 0,
            "approved_for_live": False,
            "audit_result": {
                "gate_count": 3,
                "passed_gate_count": 3,
                "failed_gate_count": 0,
            },
            "anchored_artifacts": {
                "v76_7_audit_sha256": "a" * 64,
            },
        }
        certificate["audit_certificate_sha256"] = digest(certificate)
        summary = {
            "status": "PASS",
            "audit_certificate_sha256":
                certificate["audit_certificate_sha256"],
            "v76_7_audit_sha256": "a" * 64,
        }
        result = verify_certificate(certificate, summary)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["verified"])

    def test_certificate_verifier_tamper(self):
        certificate = {
            "status": "PASS",
            "release_candidate_audit_certified": True,
            "network_allowed": False,
            "orders_submitted": 0,
            "approved_for_live": False,
            "audit_result": {
                "gate_count": 1,
                "passed_gate_count": 1,
                "failed_gate_count": 0,
            },
            "anchored_artifacts": {},
        }
        certificate["audit_certificate_sha256"] = digest(certificate)
        certificate["orders_submitted"] = 1
        summary = {
            "status": "PASS",
            "audit_certificate_sha256":
                certificate["audit_certificate_sha256"],
        }
        result = verify_certificate(certificate, summary)
        self.assertEqual(result["status"], "FAIL")
        self.assertGreater(result["error_count"], 0)

    def test_digest_deterministic(self):
        self.assertEqual(
            digest({"b": 2, "a": 1}),
            digest({"a": 1, "b": 2}),
        )


if __name__ == "__main__":
    unittest.main()
