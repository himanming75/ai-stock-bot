from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.release_candidate_closure_certificate_v76_12 import (
    ClosureError,
    digest,
    issue_closure_certificate,
    validate_config,
    write_outputs,
)
from tools.verify_release_candidate_closure_certificate_v76_12 import (
    verify_output,
)


COMMIT = "cd08119464af5c1483167878582746063c7d84c5"
HASH = "a" * 64


def config() -> dict:
    return {
        "certificate_scope": "RELEASE_CANDIDATE_CLOSURE",
        "offline_only": True,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "order_submission_allowed": False,
        "live_trading_allowed": False,
        "live_approval_allowed": False,
        "require_git_tracked_clean": True,
        "require_head_matches_origin_main": True,
        "require_framework_commit_match": True,
        "require_v76_11_self_hash_match": True,
        "require_v76_11_hash_anchor": True,
        "require_v76_11_summary_match": True,
        "require_all_v76_11_gates_pass": True,
        "require_complete_attested_chain": True,
        "require_zero_trading_side_effects": True,
        "expected_framework_commit_sha": COMMIT,
        "expected_v76_11_verification_sha256": HASH,
        "expected_v76_11_gate_count": 41,
        "v76_11_output_dir": "release/v76_11/output",
    }


def make_source(root: Path) -> str:
    out = root / "release/v76_11/output"
    out.mkdir(parents=True)
    gates = [{"gate_id": f"G{i}", "status": "PASS"} for i in range(41)]
    verification = {
        "schema_version": "test",
        "version": "76.11",
        "verification_type":
            "RELEASE_CANDIDATE_FINAL_ATTESTATION_VERIFICATION",
        "status": "PASS",
        "decision":
            "release_candidate_final_attestation_independently_verified",
        "repository": {
            "framework_commit_sha": COMMIT,
        },
        "source_attestation": {
            "status": "PASS",
            "decision": "release_candidate_final_attestation_issued",
            "release_candidate_finally_attested": True,
            "v76_10_gate_count": 36,
            "v76_10_passed_gate_count": 36,
            "v76_10_failed_gate_count": 0,
        },
        "attested_chain": {
            "v76_6_release_candidate_sealed": True,
            "v76_7_seal_independently_verified": True,
            "v76_8_audit_certified": True,
            "v76_9_audit_certificate_independently_verified": True,
        },
        "anchored_hashes": {},
        "verification_result": {
            "gate_count": 41,
            "passed_gate_count": 41,
            "failed_gate_count": 0,
            "failed_gate_ids": [],
            "gates": gates,
        },
        "final_attestation_independently_verified": True,
        "network_allowed": False,
        "broker_connected": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "next_phase": "V76_12_RELEASE_CANDIDATE_CLOSURE_CERTIFICATE",
    }
    verification["verification_sha256"] = digest(verification)
    (out / "release_candidate_final_attestation_verification_v76_11.json").write_text(
        json.dumps(verification), encoding="utf-8"
    )
    summary = {
        "status": "PASS",
        "decision":
            "release_candidate_final_attestation_independently_verified",
        "framework_commit_sha": COMMIT,
        "verification_sha256": verification["verification_sha256"],
        "gate_count": 41,
        "passed_gate_count": 41,
        "failed_gate_count": 0,
        "failed_gate_ids": [],
        "final_attestation_independently_verified": True,
        "network_allowed": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "next_phase": "V76_12_RELEASE_CANDIDATE_CLOSURE_CERTIFICATE",
    }
    (out / "release_candidate_final_attestation_verification_summary_v76_11.json").write_text(
        json.dumps(summary), encoding="utf-8"
    )
    (out / "release_candidate_final_attestation_verification_v76_11.txt").write_text(
        "PASS\n", encoding="utf-8"
    )
    return verification["verification_sha256"]


class TestV7612(unittest.TestCase):
    def test_valid_config(self):
        validate_config(config())

    def test_bad_commit_rejected(self):
        value = config()
        value["expected_framework_commit_sha"] = "bad"
        with self.assertRaises(ClosureError):
            validate_config(value)

    def test_bad_hash_rejected(self):
        value = config()
        value["expected_v76_11_verification_sha256"] = "bad"
        with self.assertRaises(ClosureError):
            validate_config(value)

    def test_wrong_gate_count_rejected(self):
        value = config()
        value["expected_v76_11_gate_count"] = 40
        with self.assertRaises(ClosureError):
            validate_config(value)

    def test_live_approval_rejected(self):
        value = config()
        value["live_approval_allowed"] = True
        with self.assertRaises(ClosureError):
            validate_config(value)

    def test_digest_deterministic(self):
        self.assertEqual(digest({"b": 2, "a": 1}),
                         digest({"a": 1, "b": 2}))

    @patch("tools.release_candidate_closure_certificate_v76_12.git_state")
    def test_certificate_pass(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_hash = make_source(root)
            cfg = config()
            cfg["expected_v76_11_verification_sha256"] = source_hash
            mocked_git.return_value = {
                "head_sha": COMMIT,
                "origin_main_sha": COMMIT,
                "branch": "main",
                "tracked_status_short": [],
                "full_status_short": [],
            }
            result = issue_closure_certificate(root, cfg)
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["release_candidate_closed"])
            self.assertEqual(
                result["closure_result"]["failed_gate_count"], 0
            )

    @patch("tools.release_candidate_closure_certificate_v76_12.git_state")
    def test_verifier_pass(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_hash = make_source(root)
            cfg = config()
            cfg["expected_v76_11_verification_sha256"] = source_hash
            mocked_git.return_value = {
                "head_sha": COMMIT,
                "origin_main_sha": COMMIT,
                "branch": "main",
                "tracked_status_short": [],
                "full_status_short": [],
            }
            result = issue_closure_certificate(root, cfg)
            out = root / "release/v76_12/output"
            write_outputs(result, out)
            verified = verify_output(out)
            self.assertTrue(verified["verified"])

    @patch("tools.release_candidate_closure_certificate_v76_12.git_state")
    def test_verifier_tamper(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_hash = make_source(root)
            cfg = config()
            cfg["expected_v76_11_verification_sha256"] = source_hash
            mocked_git.return_value = {
                "head_sha": COMMIT,
                "origin_main_sha": COMMIT,
                "branch": "main",
                "tracked_status_short": [],
                "full_status_short": [],
            }
            result = issue_closure_certificate(root, cfg)
            out = root / "release/v76_12/output"
            write_outputs(result, out)
            cert_path = out / "release_candidate_closure_certificate_v76_12.json"
            cert = json.loads(cert_path.read_text(encoding="utf-8"))
            cert["orders_submitted"] = 1
            cert_path.write_text(json.dumps(cert), encoding="utf-8")
            verified = verify_output(out)
            self.assertFalse(verified["verified"])


if __name__ == "__main__":
    unittest.main()
