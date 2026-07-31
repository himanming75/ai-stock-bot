from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from tools.release_archive_seal_v76_16 import (
    ReleaseArchiveSealError,
    build_release_archive_seal,
    digest,
    validate_config,
    write_outputs,
)
from tools.verify_release_archive_seal_v76_16 import verify_output

COMMIT = "5fa759dc70443ce883897bd8c2fbe028399476c6"


def cfg() -> dict:
    return {
        "seal_scope": "RELEASE_ARCHIVE_SEAL",
        "offline_only": True,
        "deterministic_archive_required": True,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "order_submission_allowed": False,
        "live_trading_allowed": False,
        "live_approval_allowed": False,
        "require_git_tracked_clean": True,
        "require_head_matches_origin_main": True,
        "require_framework_commit_match": True,
        "require_v76_14_outputs": True,
        "require_v76_15_outputs": True,
        "require_source_hash_anchors": True,
        "require_zero_trading_side_effects": True,
        "expected_framework_commit_sha": COMMIT,
        "expected_v76_15_verification_sha256": "a" * 64,
        "expected_v76_15_artifact_set_sha256": "b" * 64,
        "expected_v76_14_final_manifest_sha256": "c" * 64,
        "expected_v76_14_anchor_chain_sha256": "d" * 64,
        "source_files": [
            "release/v76_14/output/final_immutable_manifest_v76_14.json",
            "release/v76_14/output/final_immutable_manifest_summary_v76_14.json",
            "release/v76_14/output/final_immutable_manifest_v76_14.txt",
            "release/v76_15/output/final_integrity_verification_v76_15.json",
            "release/v76_15/output/final_integrity_verification_summary_v76_15.json",
            "release/v76_15/output/final_integrity_verification_v76_15.txt",
        ],
    }


def make_source(root: Path) -> dict:
    c = cfg()
    v14 = root / "release/v76_14/output"
    v15 = root / "release/v76_15/output"
    v14.mkdir(parents=True)
    v15.mkdir(parents=True)

    m14 = {
        "final_manifest_sha256": c["expected_v76_14_final_manifest_sha256"],
        "immutable_anchor_chain_sha256": c["expected_v76_14_anchor_chain_sha256"],
    }
    (v14 / "final_immutable_manifest_v76_14.json").write_text(
        json.dumps(m14), encoding="utf-8"
    )
    (v14 / "final_immutable_manifest_summary_v76_14.json").write_text(
        json.dumps(m14), encoding="utf-8"
    )
    (v14 / "final_immutable_manifest_v76_14.txt").write_text("PASS\n", encoding="utf-8")

    m15 = {
        "status": "PASS",
        "verification_sha256": c["expected_v76_15_verification_sha256"],
        "source": {"artifact_set_sha256": c["expected_v76_15_artifact_set_sha256"]},
        "final_manifest_independently_verified": True,
        "release_candidate_closed": True,
        "network_allowed": False,
        "broker_connected": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
    }
    (v15 / "final_integrity_verification_v76_15.json").write_text(
        json.dumps(m15), encoding="utf-8"
    )
    (v15 / "final_integrity_verification_summary_v76_15.json").write_text(
        json.dumps(m15), encoding="utf-8"
    )
    (v15 / "final_integrity_verification_v76_15.txt").write_text(
        "PASS\n", encoding="utf-8"
    )
    return c


def git_ok():
    return {
        "head_sha": COMMIT,
        "origin_main_sha": COMMIT,
        "branch": "main",
        "tracked_status_short": [],
        "full_status_short": [],
    }


class TestV7616(unittest.TestCase):
    def test_valid_config(self):
        validate_config(cfg())

    def test_bad_commit_rejected(self):
        c = cfg()
        c["expected_framework_commit_sha"] = "bad"
        with self.assertRaises(ReleaseArchiveSealError):
            validate_config(c)

    def test_live_approval_rejected(self):
        c = cfg()
        c["live_approval_allowed"] = True
        with self.assertRaises(ReleaseArchiveSealError):
            validate_config(c)

    def test_duplicate_source_rejected(self):
        c = cfg()
        c["source_files"][-1] = c["source_files"][0]
        with self.assertRaises(ReleaseArchiveSealError):
            validate_config(c)

    def test_digest_deterministic(self):
        self.assertEqual(digest({"b": 2, "a": 1}), digest({"a": 1, "b": 2}))

    @patch("tools.release_archive_seal_v76_16.git_state")
    def test_seal_pass(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = make_source(root)
            mocked_git.return_value = git_ok()
            result = build_release_archive_seal(root, c, root / "release/v76_16/output")
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["release_archive_sealed"])
            self.assertEqual(result["seal_result"]["failed_gate_count"], 0)

    @patch("tools.release_archive_seal_v76_16.git_state")
    def test_archive_hash_deterministic(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = make_source(root)
            mocked_git.return_value = git_ok()
            first = build_release_archive_seal(root, c, root / "out1")
            second = build_release_archive_seal(root, c, root / "out2")
            self.assertEqual(first["archive"]["sha256"], second["archive"]["sha256"])
            self.assertEqual(
                first["seal_certificate_sha256"], second["seal_certificate_sha256"]
            )

    @patch("tools.release_archive_seal_v76_16.git_state")
    def test_bad_anchor_fails(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = make_source(root)
            c["expected_v76_15_verification_sha256"] = "e" * 64
            mocked_git.return_value = git_ok()
            result = build_release_archive_seal(root, c, root / "out")
            self.assertEqual(result["status"], "FAIL")

    @patch("tools.release_archive_seal_v76_16.git_state")
    def test_output_verifier_pass(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = make_source(root)
            mocked_git.return_value = git_ok()
            out = root / "out"
            result = build_release_archive_seal(root, c, out)
            write_outputs(result, out)
            checked = verify_output(out)
            self.assertTrue(checked["verified"])

    @patch("tools.release_archive_seal_v76_16.git_state")
    def test_output_verifier_tampered_zip(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = make_source(root)
            mocked_git.return_value = git_ok()
            out = root / "out"
            result = build_release_archive_seal(root, c, out)
            write_outputs(result, out)
            archive = out / result["archive"]["filename"]
            with archive.open("ab") as handle:
                handle.write(b"tamper")
            checked = verify_output(out)
            self.assertFalse(checked["verified"])

    @patch("tools.release_archive_seal_v76_16.git_state")
    def test_output_verifier_tampered_certificate(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            c = make_source(root)
            mocked_git.return_value = git_ok()
            out = root / "out"
            result = build_release_archive_seal(root, c, out)
            write_outputs(result, out)
            path = out / "release_archive_seal_v76_16.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["orders_submitted"] = 1
            path.write_text(json.dumps(value), encoding="utf-8")
            checked = verify_output(out)
            self.assertFalse(checked["verified"])


if __name__ == "__main__":
    unittest.main()
