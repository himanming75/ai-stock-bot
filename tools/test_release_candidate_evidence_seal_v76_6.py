import json
import tempfile
import unittest
from pathlib import Path

from tools.release_candidate_evidence_seal_v76_6 import (
    SealError,
    build_ledger,
    build_manifest,
    digest,
    validate_config,
    verify_ledger,
)


VALID_CONFIG = {
    "seal_scope": "RELEASE_CANDIDATE_EVIDENCE_SEAL",
    "offline_only": True,
    "preserve_repository": True,
    "require_all_evidence_present": True,
    "require_prior_acceptance_pass": True,
    "require_zero_trading_side_effects": True,
    "require_tracked_file_immutability": True,
    "require_manifest_verification": True,
    "network_allowed": False,
    "broker_connection_allowed": False,
    "order_submission_allowed": False,
    "live_trading_allowed": False,
    "live_approval_allowed": False,
    "evidence_files": [{
        "evidence_id": "TEST",
        "path": "test.json",
        "required": True,
    }],
}


class TestReleaseCandidateEvidenceSealV766(unittest.TestCase):
    def test_valid_config(self):
        validate_config(dict(VALID_CONFIG))

    def test_live_approval_rejected(self):
        config = dict(VALID_CONFIG)
        config["live_approval_allowed"] = True
        with self.assertRaises(SealError):
            validate_config(config)

    def test_duplicate_evidence_rejected(self):
        config = dict(VALID_CONFIG)
        config["evidence_files"] = [
            {"evidence_id": "X", "path": "a.json", "required": True},
            {"evidence_id": "X", "path": "b.json", "required": True},
        ]
        with self.assertRaises(SealError):
            validate_config(config)

    def test_manifest_hash_deterministic(self):
        evidence = [{
            "evidence_id": "X",
            "path": "x.json",
            "size_bytes": 10,
            "file_sha256": "a" * 64,
            "status": "PASS",
            "record_sha256": "b" * 64,
        }]
        repository = {
            "commit_sha": "c" * 40,
            "origin_main_sha": "c" * 40,
            "branch": "main",
            "commit_subject": "test",
        }
        first = build_manifest(evidence, repository)
        second = build_manifest(evidence, repository)
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])

    def test_ledger_chain_verifies(self):
        evidence = [{
            "evidence_id": "X",
            "path": "x.json",
            "size_bytes": 10,
            "file_sha256": "a" * 64,
            "status": "PASS",
            "record_sha256": "b" * 64,
        }]
        manifest = {
            "manifest_sha256": "c" * 64,
        }
        ledger = build_ledger(evidence, manifest)
        result = verify_ledger(ledger)
        self.assertTrue(result["valid"])
        self.assertEqual(result["verified_entry_count"], 2)

    def test_ledger_tamper_detected(self):
        evidence = [{
            "evidence_id": "X",
            "path": "x.json",
            "size_bytes": 10,
            "file_sha256": "a" * 64,
            "status": "PASS",
            "record_sha256": "b" * 64,
        }]
        ledger = build_ledger(evidence, {"manifest_sha256": "c" * 64})
        ledger["entries"][0]["path"] = "tampered.json"
        result = verify_ledger(ledger)
        self.assertFalse(result["valid"])

    def test_digest_canonical(self):
        self.assertEqual(
            digest({"b": 2, "a": 1}),
            digest({"a": 1, "b": 2}),
        )


if __name__ == "__main__":
    unittest.main()
