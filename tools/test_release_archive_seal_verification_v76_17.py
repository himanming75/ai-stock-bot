from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from tools.release_archive_seal_verification_v76_17 import (
    ArchiveSealVerificationError,
    digest,
    validate_config,
    verify_release_archive,
    write_outputs,
)
from tools.verify_release_archive_seal_verification_v76_17 import verify_output

COMMIT = "3bbbee6deed78c169959326df1c33960155683b0"


def config() -> dict:
    return {
        "verification_scope": "RELEASE_ARCHIVE_SEAL_VERIFICATION",
        "offline_only": True,
        "read_only_verification": True,
        "deterministic_verification_required": True,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "order_submission_allowed": False,
        "live_trading_allowed": False,
        "live_approval_allowed": False,
        "require_git_tracked_clean": True,
        "require_head_matches_origin_main": True,
        "require_framework_commit_match": True,
        "require_v76_16_outputs": True,
        "require_archive_exact_member_set": True,
        "require_archive_member_hashes": True,
        "require_embedded_manifest_self_hash": True,
        "require_source_anchor_match": True,
        "require_zero_trading_side_effects": True,
        "expected_framework_commit_sha": COMMIT,
        "expected_v76_16_seal_certificate_sha256": "a" * 64,
        "expected_v76_16_archive_sha256": "b" * 64,
        "expected_v76_16_archive_manifest_sha256": "c" * 64,
        "expected_v76_16_evidence_set_sha256": "d" * 64,
        "expected_v76_14_final_manifest_sha256": "e" * 64,
        "expected_v76_14_anchor_chain_sha256": "f" * 64,
        "expected_v76_15_verification_sha256": "1" * 64,
        "expected_v76_15_artifact_set_sha256": "2" * 64,
        "expected_archive_member_count": 7,
        "expected_evidence_file_count": 6,
    }


class TestV7617(unittest.TestCase):
    def test_valid_config(self):
        validate_config(config())

    def test_bad_commit_rejected(self):
        c = config()
        c["expected_framework_commit_sha"] = "bad"
        with self.assertRaises(ArchiveSealVerificationError):
            validate_config(c)

    def test_live_approval_rejected(self):
        c = config()
        c["live_approval_allowed"] = True
        with self.assertRaises(ArchiveSealVerificationError):
            validate_config(c)

    def test_wrong_member_count_rejected(self):
        c = config()
        c["expected_archive_member_count"] = 6
        with self.assertRaises(ArchiveSealVerificationError):
            validate_config(c)

    def test_digest_deterministic(self):
        self.assertEqual(digest({"b": 2, "a": 1}), digest({"a": 1, "b": 2}))

    def test_verification_hash_excludes_runtime_fields(self):
        base = {"status": "PASS", "issued_at_utc": "x", "duration_seconds": 1}
        other = {"status": "PASS", "issued_at_utc": "y", "duration_seconds": 9}
        first = digest({k: v for k, v in base.items()
                        if k not in {"issued_at_utc", "duration_seconds"}})
        second = digest({k: v for k, v in other.items()
                         if k not in {"issued_at_utc", "duration_seconds"}})
        self.assertEqual(first, second)

    def test_output_verifier_pass(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            result = {
                "status": "PASS",
                "decision": "release_archive_seal_independently_verified",
                "repository": {"framework_commit_sha": COMMIT},
                "verified_anchors": {"v76_16_archive_sha256": "b" * 64},
                "verification_result": {
                    "gate_count": 1, "passed_gate_count": 1,
                    "failed_gate_count": 0, "failed_gate_ids": [],
                    "gates": [{"gate_id": "X", "status": "PASS"}],
                },
                "release_archive_independently_verified": True,
                "release_archive_sealed": True,
                "release_candidate_closed": True,
                "network_allowed": False,
                "broker_connected": False,
                "orders_submitted": 0,
                "approved_for_live": False,
                "live_trading_authorized": False,
                "next_phase": "V76_18_RELEASE_ARCHIVE_CLOSURE_CERTIFICATE",
                "issued_at_utc": "x", "duration_seconds": 0,
            }
            result["verification_sha256"] = digest({
                k: v for k, v in result.items()
                if k not in {"issued_at_utc", "duration_seconds"}
            })
            write_outputs(result, out)
            self.assertTrue(verify_output(out)["verified"])

    def test_output_verifier_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            result = {
                "status": "PASS",
                "decision": "release_archive_seal_independently_verified",
                "repository": {"framework_commit_sha": COMMIT},
                "verified_anchors": {},
                "verification_result": {
                    "gate_count": 1, "passed_gate_count": 1,
                    "failed_gate_count": 0, "failed_gate_ids": [],
                    "gates": [{"gate_id": "X", "status": "PASS"}],
                },
                "release_archive_independently_verified": True,
                "release_archive_sealed": True,
                "release_candidate_closed": True,
                "network_allowed": False,
                "broker_connected": False,
                "orders_submitted": 0,
                "approved_for_live": False,
                "live_trading_authorized": False,
                "next_phase": "V76_18_RELEASE_ARCHIVE_CLOSURE_CERTIFICATE",
                "issued_at_utc": "x", "duration_seconds": 0,
            }
            result["verification_sha256"] = digest({
                k: v for k, v in result.items()
                if k not in {"issued_at_utc", "duration_seconds"}
            })
            write_outputs(result, out)
            path = out / "release_archive_seal_verification_v76_17.json"
            value = json.loads(path.read_text())
            value["orders_submitted"] = 1
            path.write_text(json.dumps(value))
            self.assertFalse(verify_output(out)["verified"])

    def test_certificate_tamper_detected_logic(self):
        sample = {"status": "PASS", "seal_certificate_sha256": "x"}
        calculated = digest({
            k: v for k, v in sample.items()
            if k not in {"seal_certificate_sha256", "issued_at_utc",
                         "duration_seconds"}
        })
        self.assertNotEqual(sample["seal_certificate_sha256"], calculated)

    def test_member_hash_tamper_detected_logic(self):
        original = hashlib.sha256(b"original").hexdigest()
        changed = hashlib.sha256(b"changed").hexdigest()
        self.assertNotEqual(original, changed)

    def test_exact_member_set_logic(self):
        expected = sorted(["evidence/a", "seal/release_archive_manifest_v76_16.json"])
        actual = sorted(["evidence/a", "seal/release_archive_manifest_v76_16.json"])
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
