from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.final_integrity_verification_v76_15 import (
    IntegrityVerificationError,
    build_final_integrity_verification,
    digest,
    validate_config,
    write_outputs,
)
from tools.verify_final_integrity_verification_v76_15 import verify_output

COMMIT = "4faf83a560767a0a963d045f1560712e1d1b0135"
MANIFEST_HASH = "a" * 64
ANCHOR_HASH = "b" * 64


def config() -> dict:
    return {
        "verification_scope": "FINAL_INTEGRITY_VERIFICATION",
        "offline_only": True,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "order_submission_allowed": False,
        "live_trading_allowed": False,
        "live_approval_allowed": False,
        "require_git_tracked_clean": True,
        "require_head_matches_origin_main": True,
        "require_framework_commit_match": True,
        "require_manifest_self_hash_match": True,
        "require_anchor_chain_hash_match": True,
        "require_summary_match": True,
        "require_all_v76_14_gates_pass": True,
        "require_final_manifest_issued": True,
        "require_release_candidate_closed": True,
        "require_zero_trading_side_effects": True,
        "require_source_files_present": True,
        "expected_framework_commit_sha": COMMIT,
        "expected_final_manifest_sha256": MANIFEST_HASH,
        "expected_immutable_anchor_chain_sha256": ANCHOR_HASH,
        "expected_v76_14_gate_count": 69,
        "v76_14_output_dir": "release/v76_14/output",
    }


def make_source(root: Path) -> tuple[str, str]:
    out = root / "release/v76_14/output"
    out.mkdir(parents=True)
    anchors = {"v76_6": {"commit_sha": "1" * 40}}
    gates = [{"gate_id": f"G{i}", "status": "PASS"} for i in range(69)]
    manifest = {
        "schema_version": "test",
        "version": "76.14",
        "manifest_type": "FINAL_IMMUTABLE_MANIFEST",
        "issued_at_utc": "2026-01-01T00:00:00+00:00",
        "duration_seconds": 0.1,
        "status": "PASS",
        "decision": "final_immutable_manifest_issued",
        "repository": {"framework_commit_sha": COMMIT},
        "immutable_anchor_chain": anchors,
        "immutable_anchor_chain_sha256": digest(anchors),
        "manifest_result": {
            "gate_count": 69,
            "passed_gate_count": 69,
            "failed_gate_count": 0,
            "failed_gate_ids": [],
            "gates": gates,
        },
        "final_manifest_issued": True,
        "release_candidate_closed": True,
        "network_allowed": False,
        "broker_connected": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "next_phase": "V76_15_FINAL_INTEGRITY_VERIFICATION",
    }
    immutable = {
        key: value for key, value in manifest.items()
        if key not in {"issued_at_utc", "duration_seconds"}
    }
    manifest["final_manifest_sha256"] = digest(immutable)

    summary = {
        "status": "PASS",
        "decision": "final_immutable_manifest_issued",
        "framework_commit_sha": COMMIT,
        "final_manifest_sha256": manifest["final_manifest_sha256"],
        "immutable_anchor_chain_sha256": manifest[
            "immutable_anchor_chain_sha256"
        ],
        "gate_count": 69,
        "passed_gate_count": 69,
        "failed_gate_count": 0,
        "failed_gate_ids": [],
        "final_manifest_issued": True,
        "release_candidate_closed": True,
        "network_allowed": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "next_phase": "V76_15_FINAL_INTEGRITY_VERIFICATION",
    }

    (out / "final_immutable_manifest_v76_14.json").write_text(
        json.dumps(manifest, sort_keys=True), encoding="utf-8"
    )
    (out / "final_immutable_manifest_summary_v76_14.json").write_text(
        json.dumps(summary, sort_keys=True), encoding="utf-8"
    )
    (out / "final_immutable_manifest_v76_14.txt").write_text(
        "PASS\n", encoding="utf-8"
    )
    return (
        manifest["final_manifest_sha256"],
        manifest["immutable_anchor_chain_sha256"],
    )


def git_ok():
    return {
        "head_sha": COMMIT,
        "origin_main_sha": COMMIT,
        "branch": "main",
        "tracked_status_short": [],
        "full_status_short": [],
    }


class TestV7615(unittest.TestCase):
    def test_valid_config(self):
        validate_config(config())

    def test_bad_commit_rejected(self):
        value = config()
        value["expected_framework_commit_sha"] = "bad"
        with self.assertRaises(IntegrityVerificationError):
            validate_config(value)

    def test_bad_hash_rejected(self):
        value = config()
        value["expected_final_manifest_sha256"] = "bad"
        with self.assertRaises(IntegrityVerificationError):
            validate_config(value)

    def test_live_approval_rejected(self):
        value = config()
        value["live_approval_allowed"] = True
        with self.assertRaises(IntegrityVerificationError):
            validate_config(value)

    def test_digest_deterministic(self):
        self.assertEqual(
            digest({"b": 2, "a": 1}),
            digest({"a": 1, "b": 2}),
        )

    @patch("tools.final_integrity_verification_v76_15.git_state")
    def test_verification_pass(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_hash, anchor_hash = make_source(root)
            cfg = config()
            cfg["expected_final_manifest_sha256"] = manifest_hash
            cfg["expected_immutable_anchor_chain_sha256"] = anchor_hash
            mocked_git.return_value = git_ok()
            result = build_final_integrity_verification(root, cfg)
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["final_manifest_independently_verified"])
            self.assertEqual(result["verification_result"]["failed_gate_count"], 0)

    @patch("tools.final_integrity_verification_v76_15.git_state")
    def test_verification_hash_deterministic(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_hash, anchor_hash = make_source(root)
            cfg = config()
            cfg["expected_final_manifest_sha256"] = manifest_hash
            cfg["expected_immutable_anchor_chain_sha256"] = anchor_hash
            mocked_git.return_value = git_ok()
            first = build_final_integrity_verification(root, cfg)
            second = build_final_integrity_verification(root, cfg)
            self.assertEqual(
                first["verification_sha256"],
                second["verification_sha256"],
            )

    @patch("tools.final_integrity_verification_v76_15.git_state")
    def test_manifest_tamper_rejected(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_hash, anchor_hash = make_source(root)
            path = root / (
                "release/v76_14/output/final_immutable_manifest_v76_14.json"
            )
            value = json.loads(path.read_text(encoding="utf-8"))
            value["orders_submitted"] = 1
            path.write_text(json.dumps(value), encoding="utf-8")
            cfg = config()
            cfg["expected_final_manifest_sha256"] = manifest_hash
            cfg["expected_immutable_anchor_chain_sha256"] = anchor_hash
            mocked_git.return_value = git_ok()
            result = build_final_integrity_verification(root, cfg)
            self.assertEqual(result["status"], "FAIL")
            self.assertIn(
                "V76_14_MANIFEST_SELF_HASH",
                result["verification_result"]["failed_gate_ids"],
            )

    @patch("tools.final_integrity_verification_v76_15.git_state")
    def test_summary_tamper_rejected(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_hash, anchor_hash = make_source(root)
            path = root / (
                "release/v76_14/output/"
                "final_immutable_manifest_summary_v76_14.json"
            )
            value = json.loads(path.read_text(encoding="utf-8"))
            value["status"] = "FAIL"
            path.write_text(json.dumps(value), encoding="utf-8")
            cfg = config()
            cfg["expected_final_manifest_sha256"] = manifest_hash
            cfg["expected_immutable_anchor_chain_sha256"] = anchor_hash
            mocked_git.return_value = git_ok()
            result = build_final_integrity_verification(root, cfg)
            self.assertEqual(result["status"], "FAIL")
            self.assertIn(
                "V76_14_SUMMARY_STATUS",
                result["verification_result"]["failed_gate_ids"],
            )

    @patch("tools.final_integrity_verification_v76_15.git_state")
    def test_output_verifier_pass(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_hash, anchor_hash = make_source(root)
            cfg = config()
            cfg["expected_final_manifest_sha256"] = manifest_hash
            cfg["expected_immutable_anchor_chain_sha256"] = anchor_hash
            mocked_git.return_value = git_ok()
            result = build_final_integrity_verification(root, cfg)
            out = root / "release/v76_15/output"
            write_outputs(result, out)
            checked = verify_output(out)
            self.assertTrue(checked["verified"])

    @patch("tools.final_integrity_verification_v76_15.git_state")
    def test_output_verifier_tamper(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_hash, anchor_hash = make_source(root)
            cfg = config()
            cfg["expected_final_manifest_sha256"] = manifest_hash
            cfg["expected_immutable_anchor_chain_sha256"] = anchor_hash
            mocked_git.return_value = git_ok()
            result = build_final_integrity_verification(root, cfg)
            out = root / "release/v76_15/output"
            write_outputs(result, out)
            path = out / "final_integrity_verification_v76_15.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["orders_submitted"] = 1
            path.write_text(json.dumps(value), encoding="utf-8")
            checked = verify_output(out)
            self.assertFalse(checked["verified"])


if __name__ == "__main__":
    unittest.main()
