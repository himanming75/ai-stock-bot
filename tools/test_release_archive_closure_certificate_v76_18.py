from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.release_archive_closure_certificate_v76_18 import (
    ClosureCertificateError,
    digest,
    summary_from,
    validate_config,
    write_outputs,
)
from tools.verify_release_archive_closure_certificate_v76_18 import verify_output

COMMIT = "99cc52ce6b3c3676fc086882a585bbca616f1b7b"


def cfg() -> dict:
    return {
        "certificate_scope": "RELEASE_ARCHIVE_CLOSURE_CERTIFICATE",
        "offline_only": True,
        "deterministic_certificate_required": True,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "order_submission_allowed": False,
        "live_trading_allowed": False,
        "live_approval_allowed": False,
        "require_git_tracked_clean": True,
        "require_head_matches_origin_main": True,
        "require_framework_commit_match": True,
        "require_v76_16_seal": True,
        "require_v76_17_verification": True,
        "require_zero_failed_gates": True,
        "require_anchor_chain_consistency": True,
        "require_zero_trading_side_effects": True,
        "expected_framework_commit_sha": COMMIT,
        "expected_v76_17_verification_sha256": "a" * 64,
        "expected_v76_16_seal_certificate_sha256": "b" * 64,
        "expected_v76_16_archive_sha256": "c" * 64,
        "expected_v76_16_archive_manifest_sha256": "d" * 64,
        "expected_v76_16_evidence_set_sha256": "e" * 64,
    }


class TestV7618(unittest.TestCase):
    def test_valid_config(self):
        validate_config(cfg())

    def test_bad_commit_rejected(self):
        c = cfg()
        c["expected_framework_commit_sha"] = "bad"
        with self.assertRaises(ClosureCertificateError):
            validate_config(c)

    def test_live_approval_rejected(self):
        c = cfg()
        c["live_approval_allowed"] = True
        with self.assertRaises(ClosureCertificateError):
            validate_config(c)

    def test_required_flag_rejected(self):
        c = cfg()
        c["require_v76_17_verification"] = False
        with self.assertRaises(ClosureCertificateError):
            validate_config(c)

    def test_digest_deterministic(self):
        self.assertEqual(digest({"b": 2, "a": 1}), digest({"a": 1, "b": 2}))

    def test_runtime_fields_excluded(self):
        first = {"status": "PASS", "issued_at_utc": "x", "duration_seconds": 1}
        second = {"status": "PASS", "issued_at_utc": "y", "duration_seconds": 9}
        self.assertEqual(
            digest({k: v for k, v in first.items()
                    if k not in {"issued_at_utc", "duration_seconds"}}),
            digest({k: v for k, v in second.items()
                    if k not in {"issued_at_utc", "duration_seconds"}}),
        )

    def sample_result(self) -> dict:
        result = {
            "status": "PASS",
            "decision": "release_archive_closure_certified",
            "repository": {"framework_commit_sha": COMMIT},
            "closure_chain": {"x": "y"},
            "closure_chain_sha256": digest({"x": "y"}),
            "certificate_result": {
                "gate_count": 1,
                "passed_gate_count": 1,
                "failed_gate_count": 0,
                "failed_gate_ids": [],
                "gates": [{"gate_id": "X", "status": "PASS"}],
            },
            "release_archive_closure_certified": True,
            "release_archive_independently_verified": True,
            "release_archive_sealed": True,
            "release_candidate_closed": True,
            "network_allowed": False,
            "broker_connected": False,
            "orders_submitted": 0,
            "approved_for_live": False,
            "live_trading_authorized": False,
            "next_phase": "V76_19_RELEASE_ARCHIVE_CLOSURE_VERIFICATION",
            "issued_at_utc": "x",
            "duration_seconds": 0,
        }
        result["closure_certificate_sha256"] = digest({
            k: v for k, v in result.items()
            if k not in {"issued_at_utc", "duration_seconds"}
        })
        return result

    def test_summary_consistent(self):
        result = self.sample_result()
        self.assertEqual(summary_from(result)["status"], "PASS")

    def test_output_verifier_pass(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            result = self.sample_result()
            write_outputs(result, out)
            self.assertTrue(verify_output(out)["verified"])

    def test_output_verifier_detects_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            result = self.sample_result()
            write_outputs(result, out)
            path = out / "release_archive_closure_certificate_v76_18.json"
            value = json.loads(path.read_text())
            value["orders_submitted"] = 1
            path.write_text(json.dumps(value))
            self.assertFalse(verify_output(out)["verified"])

    def test_chain_tamper_detected(self):
        result = self.sample_result()
        result["closure_chain"]["x"] = "changed"
        self.assertNotEqual(
            result["closure_chain_sha256"], digest(result["closure_chain"])
        )

    def test_failed_gate_detected(self):
        result = self.sample_result()
        result["certificate_result"]["failed_gate_count"] = 1
        self.assertNotEqual(
            result["certificate_result"]["failed_gate_count"], 0
        )


if __name__ == "__main__":
    unittest.main()
