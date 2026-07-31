from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.release_candidate_closure_verification_v76_13 import (
    VerificationError,
    digest,
    validate_config,
    verify_closure_certificate,
    write_outputs,
)
from tools.verify_release_candidate_closure_verification_v76_13 import (
    verify_output,
)


COMMIT = "55c3e61b2318a07f69bc99d6969685330ea14e4d"
HASH = "a" * 64


def config() -> dict:
    return {
        "verification_scope":
            "RELEASE_CANDIDATE_CLOSURE_VERIFICATION",
        "offline_only": True,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "order_submission_allowed": False,
        "live_trading_allowed": False,
        "live_approval_allowed": False,
        "require_git_tracked_clean": True,
        "require_head_matches_origin_main": True,
        "require_framework_commit_match": True,
        "require_closure_self_hash_match": True,
        "require_closure_hash_anchor": True,
        "require_closure_summary_match": True,
        "require_all_closure_gates_pass": True,
        "require_release_candidate_closed": True,
        "require_zero_trading_side_effects": True,
        "expected_framework_commit_sha": COMMIT,
        "expected_v76_12_closure_certificate_sha256": HASH,
        "expected_v76_12_gate_count": 45,
        "v76_12_output_dir": "release/v76_12/output",
    }


def make_source(root: Path) -> str:
    out = root / "release/v76_12/output"
    out.mkdir(parents=True)
    gates = [
        {"gate_id": f"G{i}", "status": "PASS"}
        for i in range(45)
    ]
    cert = {
        "schema_version": "test",
        "version": "76.12",
        "certificate_type": "RELEASE_CANDIDATE_CLOSURE_CERTIFICATE",
        "status": "PASS",
        "decision": "release_candidate_closure_certificate_issued",
        "repository": {
            "framework_commit_sha": COMMIT,
        },
        "source_verification": {
            "status": "PASS",
            "decision":
                "release_candidate_final_attestation_independently_verified",
            "final_attestation_independently_verified": True,
            "v76_11_gate_count": 41,
            "v76_11_passed_gate_count": 41,
            "v76_11_failed_gate_count": 0,
        },
        "attested_chain": {
            "v76_6_release_candidate_sealed": True,
            "v76_7_seal_independently_verified": True,
            "v76_8_audit_certified": True,
            "v76_9_audit_certificate_independently_verified": True,
        },
        "anchored_hashes": {},
        "closure_result": {
            "gate_count": 45,
            "passed_gate_count": 45,
            "failed_gate_count": 0,
            "failed_gate_ids": [],
            "gates": gates,
        },
        "release_candidate_closed": True,
        "network_allowed": False,
        "broker_connected": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "next_phase":
            "V76_13_RELEASE_CANDIDATE_CLOSURE_VERIFICATION",
    }
    cert["closure_certificate_sha256"] = digest(cert)
    (out / "release_candidate_closure_certificate_v76_12.json").write_text(
        json.dumps(cert), encoding="utf-8"
    )

    summary = {
        "status": "PASS",
        "decision": "release_candidate_closure_certificate_issued",
        "framework_commit_sha": COMMIT,
        "closure_certificate_sha256":
            cert["closure_certificate_sha256"],
        "gate_count": 45,
        "passed_gate_count": 45,
        "failed_gate_count": 0,
        "failed_gate_ids": [],
        "release_candidate_closed": True,
        "network_allowed": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "next_phase":
            "V76_13_RELEASE_CANDIDATE_CLOSURE_VERIFICATION",
    }
    (
        out
        / "release_candidate_closure_certificate_summary_v76_12.json"
    ).write_text(json.dumps(summary), encoding="utf-8")
    (
        out / "release_candidate_closure_certificate_v76_12.txt"
    ).write_text("PASS\n", encoding="utf-8")
    return cert["closure_certificate_sha256"]


class TestV7613(unittest.TestCase):
    def test_valid_config(self):
        validate_config(config())

    def test_bad_commit_rejected(self):
        value = config()
        value["expected_framework_commit_sha"] = "bad"
        with self.assertRaises(VerificationError):
            validate_config(value)

    def test_bad_hash_rejected(self):
        value = config()
        value["expected_v76_12_closure_certificate_sha256"] = "bad"
        with self.assertRaises(VerificationError):
            validate_config(value)

    def test_wrong_gate_count_rejected(self):
        value = config()
        value["expected_v76_12_gate_count"] = 44
        with self.assertRaises(VerificationError):
            validate_config(value)

    def test_live_approval_rejected(self):
        value = config()
        value["live_approval_allowed"] = True
        with self.assertRaises(VerificationError):
            validate_config(value)

    def test_digest_deterministic(self):
        self.assertEqual(
            digest({"b": 2, "a": 1}),
            digest({"a": 1, "b": 2}),
        )

    @patch(
        "tools.release_candidate_closure_verification_v76_13.git_state"
    )
    def test_verification_pass(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_hash = make_source(root)
            cfg = config()
            cfg["expected_v76_12_closure_certificate_sha256"] = source_hash
            mocked_git.return_value = {
                "head_sha": COMMIT,
                "origin_main_sha": COMMIT,
                "branch": "main",
                "tracked_status_short": [],
                "full_status_short": [],
            }
            result = verify_closure_certificate(root, cfg)
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(
                result["closure_certificate_independently_verified"]
            )
            self.assertEqual(
                result["verification_result"]["failed_gate_count"],
                0,
            )

    @patch(
        "tools.release_candidate_closure_verification_v76_13.git_state"
    )
    def test_output_verifier_pass(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_hash = make_source(root)
            cfg = config()
            cfg["expected_v76_12_closure_certificate_sha256"] = source_hash
            mocked_git.return_value = {
                "head_sha": COMMIT,
                "origin_main_sha": COMMIT,
                "branch": "main",
                "tracked_status_short": [],
                "full_status_short": [],
            }
            result = verify_closure_certificate(root, cfg)
            out = root / "release/v76_13/output"
            write_outputs(result, out)
            checked = verify_output(out)
            self.assertTrue(checked["verified"])

    @patch(
        "tools.release_candidate_closure_verification_v76_13.git_state"
    )
    def test_output_verifier_tamper(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_hash = make_source(root)
            cfg = config()
            cfg["expected_v76_12_closure_certificate_sha256"] = source_hash
            mocked_git.return_value = {
                "head_sha": COMMIT,
                "origin_main_sha": COMMIT,
                "branch": "main",
                "tracked_status_short": [],
                "full_status_short": [],
            }
            result = verify_closure_certificate(root, cfg)
            out = root / "release/v76_13/output"
            write_outputs(result, out)
            path = (
                out
                / "release_candidate_closure_verification_v76_13.json"
            )
            value = json.loads(path.read_text(encoding="utf-8"))
            value["orders_submitted"] = 1
            path.write_text(json.dumps(value), encoding="utf-8")
            checked = verify_output(out)
            self.assertFalse(checked["verified"])


if __name__ == "__main__":
    unittest.main()
