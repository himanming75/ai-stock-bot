import unittest

from tools.release_candidate_seal_verification_v76_7 import (
    AuditError,
    digest,
    validate_config,
    verify_internal_object_hash,
    verify_ledger_chain,
)


VALID = {
    "verification_scope": "RELEASE_CANDIDATE_SEAL_VERIFICATION",
    "offline_only": True,
    "require_git_clean": True,
    "require_head_matches_origin_main": True,
    "require_sealed_commit_match": True,
    "require_all_hashes_match": True,
    "require_all_evidence_files_match": True,
    "require_zero_trading_side_effects": True,
    "network_allowed": False,
    "broker_connection_allowed": False,
    "order_submission_allowed": False,
    "live_trading_allowed": False,
    "live_approval_allowed": False,
    "expected_sealed_commit_sha": "a" * 40,
    "expected_hashes": {
        "manifest_sha256": "b" * 64,
        "ledger_sha256": "c" * 64,
        "certificate_sha256": "d" * 64,
        "release_seal_sha256": "e" * 64,
    },
    "v76_6_output_dir": "release/v76_6/output",
}


class TestReleaseCandidateSealVerificationV767(unittest.TestCase):
    def test_valid_config(self):
        validate_config(dict(VALID))

    def test_network_rejected(self):
        config = dict(VALID)
        config["network_allowed"] = True
        with self.assertRaises(AuditError):
            validate_config(config)

    def test_bad_commit_rejected(self):
        config = dict(VALID)
        config["expected_sealed_commit_sha"] = "bad"
        with self.assertRaises(AuditError):
            validate_config(config)

    def test_bad_hash_rejected(self):
        config = dict(VALID)
        config["expected_hashes"] = dict(VALID["expected_hashes"])
        config["expected_hashes"]["manifest_sha256"] = "x" * 64
        with self.assertRaises(AuditError):
            validate_config(config)

    def test_internal_hash_pass(self):
        value = {"status": "PASS"}
        value["object_sha256"] = digest(value)
        passed, stored, calculated = verify_internal_object_hash(
            value, "object_sha256"
        )
        self.assertTrue(passed)
        self.assertEqual(stored, calculated)

    def test_internal_hash_tamper(self):
        value = {"status": "PASS"}
        value["object_sha256"] = digest(value)
        value["status"] = "FAIL"
        passed, _, _ = verify_internal_object_hash(value, "object_sha256")
        self.assertFalse(passed)

    def test_ledger_chain_pass(self):
        first = {
            "sequence": 1,
            "evidence_id": "A",
            "previous_entry_sha256": "0" * 64,
        }
        first["entry_sha256"] = digest(first)
        second = {
            "sequence": 2,
            "evidence_id": "B",
            "previous_entry_sha256": first["entry_sha256"],
        }
        second["entry_sha256"] = digest(second)
        valid, errors = verify_ledger_chain({
            "entries": [first, second],
            "ledger_head_sha256": second["entry_sha256"],
        })
        self.assertTrue(valid)
        self.assertEqual(errors, [])

    def test_ledger_chain_tamper(self):
        first = {
            "sequence": 1,
            "evidence_id": "A",
            "previous_entry_sha256": "0" * 64,
        }
        first["entry_sha256"] = digest(first)
        first["evidence_id"] = "TAMPER"
        valid, errors = verify_ledger_chain({
            "entries": [first],
            "ledger_head_sha256": first["entry_sha256"],
        })
        self.assertFalse(valid)
        self.assertTrue(errors)

    def test_tracked_only_clean_gate_is_used(self):
        from pathlib import Path
        source = Path(
            "tools/release_candidate_seal_verification_v76_7.py"
        ).read_text(encoding="utf-8")
        self.assertIn("GIT_TRACKED_WORKING_TREE_CLEAN", source)
        self.assertIn("--untracked-files=no", source)
        self.assertNotIn(
            'verify_hash_field(gates, "GIT_WORKING_TREE_CLEAN"',
            source,
        )

    def test_digest_deterministic(self):
        self.assertEqual(digest({"b": 2, "a": 1}), digest({"a": 1, "b": 2}))


if __name__ == "__main__":
    unittest.main()
