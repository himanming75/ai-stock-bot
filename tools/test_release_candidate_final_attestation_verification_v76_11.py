from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.release_candidate_final_attestation_verification_v76_11 import (
    VerificationError,
    digest,
    validate_config,
    verify_final_attestation,
    write_outputs,
)
from tools.verify_release_candidate_final_attestation_verification_v76_11 import (
    verify_output,
)


COMMIT = "7a438b825f14fd078b0c0de5fefecb08c6ad3a41"


def config() -> dict:
    return {
        "verification_scope": "FINAL_ATTESTATION_VERIFICATION",
        "offline_only": True,
        "require_git_tracked_clean": True,
        "require_head_matches_origin_main": True,
        "require_framework_commit_match": True,
        "require_attestation_self_hash_match": True,
        "require_attestation_hash_anchor": True,
        "require_attestation_summary_match": True,
        "require_all_attestation_gates_pass": True,
        "require_attested_chain_complete": True,
        "require_zero_trading_side_effects": True,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "order_submission_allowed": False,
        "live_trading_allowed": False,
        "live_approval_allowed": False,
        "expected_framework_commit_sha": COMMIT,
        "expected_v76_10_final_attestation_sha256": "a" * 64,
        "expected_v76_10_source_framework_commit_sha": "09db70f69560314c989d074973cbfd0a493848e7",
        "expected_v76_10_gate_count": 36,
        "v76_10_output_dir": "release/v76_10/output",
    }


class TestV7611(unittest.TestCase):
    def test_digest_deterministic(self):
        self.assertEqual(digest({"b": 2, "a": 1}), digest({"a": 1, "b": 2}))

    def test_valid_config(self):
        validate_config(config())

    def test_bad_commit_rejected(self):
        value = config()
        value["expected_framework_commit_sha"] = "bad"
        with self.assertRaises(VerificationError):
            validate_config(value)

    def test_bad_hash_rejected(self):
        value = config()
        value["expected_v76_10_final_attestation_sha256"] = "bad"
        with self.assertRaises(VerificationError):
            validate_config(value)

    def test_live_approval_rejected(self):
        value = config()
        value["live_approval_allowed"] = True
        with self.assertRaises(VerificationError):
            validate_config(value)

    def test_source_framework_commit_is_distinct_from_verifier_commit(self):
        value = config()
        self.assertNotEqual(
            value["expected_framework_commit_sha"],
            value["expected_v76_10_source_framework_commit_sha"],
        )
        validate_config(value)

    def test_wrong_gate_count_rejected(self):
        value = config()
        value["expected_v76_10_gate_count"] = 35
        with self.assertRaises(VerificationError):
            validate_config(value)

    def test_verifier_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            value = {
                "status": "PASS",
                "final_attestation_independently_verified": True,
                "verification_result": {
                    "gate_count": 3,
                    "passed_gate_count": 3,
                    "failed_gate_count": 0,
                },
                "network_allowed": False,
                "orders_submitted": 0,
                "approved_for_live": False,
                "live_trading_authorized": False,
                "next_phase": "V76_12_RELEASE_CANDIDATE_CLOSURE_CERTIFICATE",
            }
            value["verification_sha256"] = digest(value)
            path = (
                output
                / "release_candidate_final_attestation_verification_v76_11.json"
            )
            path.write_text(__import__("json").dumps(value), encoding="utf-8")
            self.assertTrue(verify_output(output)["verified"])

    def test_verifier_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            value = {
                "status": "PASS",
                "final_attestation_independently_verified": True,
                "verification_result": {
                    "gate_count": 1,
                    "passed_gate_count": 1,
                    "failed_gate_count": 0,
                },
                "network_allowed": False,
                "orders_submitted": 0,
                "approved_for_live": False,
                "live_trading_authorized": False,
                "next_phase": "V76_12_RELEASE_CANDIDATE_CLOSURE_CERTIFICATE",
            }
            value["verification_sha256"] = digest(value)
            value["orders_submitted"] = 1
            path = (
                output
                / "release_candidate_final_attestation_verification_v76_11.json"
            )
            path.write_text(__import__("json").dumps(value), encoding="utf-8")
            result = verify_output(output)
            self.assertFalse(result["verified"])
            self.assertGreater(result["error_count"], 0)


if __name__ == "__main__":
    unittest.main()
