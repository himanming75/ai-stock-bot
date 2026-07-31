from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.final_immutable_manifest_v76_14 import (
    ManifestError,
    build_final_immutable_manifest,
    digest,
    validate_config,
    write_outputs,
)
from tools.verify_final_immutable_manifest_v76_14 import verify_output


COMMIT = "c39fd1af94c1fead939927d4646ba8c4231fe664"
HASH = "a" * 64


def anchors() -> dict:
    data = {}
    for i in range(6, 14):
        data[f"v76_{i}"] = {
            "commit_sha": f"{i:040x}"[-40:],
            "artifact_sha256": f"{i:064x}"[-64:],
        }
    data["v76_13"]["commit_sha"] = COMMIT
    data["v76_13"]["verification_sha256"] = HASH
    del data["v76_13"]["artifact_sha256"]
    return data


def config() -> dict:
    return {
        "manifest_scope": "FINAL_IMMUTABLE_MANIFEST",
        "offline_only": True,
        "network_allowed": False,
        "broker_connection_allowed": False,
        "order_submission_allowed": False,
        "live_trading_allowed": False,
        "live_approval_allowed": False,
        "require_git_tracked_clean": True,
        "require_head_matches_origin_main": True,
        "require_framework_commit_match": True,
        "require_v76_13_self_hash_match": True,
        "require_v76_13_hash_anchor": True,
        "require_v76_13_summary_match": True,
        "require_all_v76_13_gates_pass": True,
        "require_release_candidate_closed": True,
        "require_complete_anchor_chain": True,
        "require_zero_trading_side_effects": True,
        "expected_framework_commit_sha": COMMIT,
        "expected_v76_13_verification_sha256": HASH,
        "expected_v76_13_gate_count": 45,
        "v76_13_output_dir": "release/v76_13/output",
        "immutable_anchor_chain": anchors(),
    }


def make_source(root: Path) -> str:
    out = root / "release/v76_13/output"
    out.mkdir(parents=True)
    gates = [{"gate_id": f"G{i}", "status": "PASS"} for i in range(45)]
    verification = {
        "schema_version": "test",
        "version": "76.13",
        "verification_type":
            "RELEASE_CANDIDATE_CLOSURE_CERTIFICATE_VERIFICATION",
        "status": "PASS",
        "decision":
            "release_candidate_closure_certificate_independently_verified",
        "repository": {
            "framework_commit_sha": COMMIT,
        },
        "verification_result": {
            "gate_count": 45,
            "passed_gate_count": 45,
            "failed_gate_count": 0,
            "failed_gate_ids": [],
            "gates": gates,
        },
        "closure_certificate_independently_verified": True,
        "release_candidate_closed": True,
        "network_allowed": False,
        "broker_connected": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "next_phase": "V76_14_FINAL_IMMUTABLE_MANIFEST",
    }
    verification["verification_sha256"] = digest(verification)
    (
        out / "release_candidate_closure_verification_v76_13.json"
    ).write_text(json.dumps(verification), encoding="utf-8")

    summary = {
        "status": "PASS",
        "decision":
            "release_candidate_closure_certificate_independently_verified",
        "framework_commit_sha": COMMIT,
        "verification_sha256": verification["verification_sha256"],
        "gate_count": 45,
        "passed_gate_count": 45,
        "failed_gate_count": 0,
        "failed_gate_ids": [],
        "closure_certificate_independently_verified": True,
        "release_candidate_closed": True,
        "network_allowed": False,
        "orders_submitted": 0,
        "approved_for_live": False,
        "live_trading_authorized": False,
        "next_phase": "V76_14_FINAL_IMMUTABLE_MANIFEST",
    }
    (
        out / "release_candidate_closure_verification_summary_v76_13.json"
    ).write_text(json.dumps(summary), encoding="utf-8")
    (
        out / "release_candidate_closure_verification_v76_13.txt"
    ).write_text("PASS\n", encoding="utf-8")
    return verification["verification_sha256"]


class TestV7614(unittest.TestCase):
    def test_valid_config(self):
        value = config()
        value["expected_v76_13_verification_sha256"] = (
            value["immutable_anchor_chain"]["v76_13"]["verification_sha256"]
        )
        validate_config(value)

    def test_bad_commit_rejected(self):
        value = config()
        value["expected_framework_commit_sha"] = "bad"
        with self.assertRaises(ManifestError):
            validate_config(value)

    def test_bad_hash_rejected(self):
        value = config()
        value["expected_v76_13_verification_sha256"] = "bad"
        with self.assertRaises(ManifestError):
            validate_config(value)

    def test_missing_anchor_rejected(self):
        value = config()
        del value["immutable_anchor_chain"]["v76_8"]
        with self.assertRaises(ManifestError):
            validate_config(value)

    def test_live_approval_rejected(self):
        value = config()
        value["live_approval_allowed"] = True
        with self.assertRaises(ManifestError):
            validate_config(value)

    def test_digest_deterministic(self):
        self.assertEqual(
            digest({"b": 2, "a": 1}),
            digest({"a": 1, "b": 2}),
        )

    @patch("tools.final_immutable_manifest_v76_14.git_state")
    def test_manifest_pass_with_sorted_json_anchor_order(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_hash = make_source(root)
            cfg = config()
            cfg["expected_v76_13_verification_sha256"] = source_hash
            cfg["immutable_anchor_chain"]["v76_13"]["verification_sha256"] = source_hash

            config_path = root / "sorted_config.json"
            config_path.write_text(
                json.dumps(cfg, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            sorted_cfg = json.loads(config_path.read_text(encoding="utf-8"))

            mocked_git.return_value = {
                "head_sha": COMMIT,
                "origin_main_sha": COMMIT,
                "branch": "main",
                "tracked_status_short": [],
                "full_status_short": [],
            }
            result = build_final_immutable_manifest(root, sorted_cfg)
            self.assertEqual(result["status"], "PASS")
            self.assertNotIn(
                "IMMUTABLE_ANCHOR_VERSION_SET",
                result["manifest_result"]["failed_gate_ids"],
            )

    @patch("tools.final_immutable_manifest_v76_14.git_state")
    def test_manifest_pass(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_hash = make_source(root)
            cfg = config()
            cfg["expected_v76_13_verification_sha256"] = source_hash
            cfg["immutable_anchor_chain"]["v76_13"]["verification_sha256"] = source_hash
            mocked_git.return_value = {
                "head_sha": COMMIT,
                "origin_main_sha": COMMIT,
                "branch": "main",
                "tracked_status_short": [],
                "full_status_short": [],
            }
            result = build_final_immutable_manifest(root, cfg)
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["final_manifest_issued"])
            self.assertEqual(result["manifest_result"]["failed_gate_count"], 0)

    @patch("tools.final_immutable_manifest_v76_14.git_state")
    def test_final_manifest_hash_deterministic_across_runs(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_hash = make_source(root)
            cfg = config()
            cfg["expected_v76_13_verification_sha256"] = source_hash
            cfg["immutable_anchor_chain"]["v76_13"]["verification_sha256"] = source_hash
            mocked_git.return_value = {
                "head_sha": COMMIT,
                "origin_main_sha": COMMIT,
                "branch": "main",
                "tracked_status_short": [],
                "full_status_short": [],
            }

            first = build_final_immutable_manifest(root, cfg)
            second = build_final_immutable_manifest(root, cfg)

            self.assertNotEqual(
                first["issued_at_utc"],
                "",
            )
            self.assertEqual(
                first["final_manifest_sha256"],
                second["final_manifest_sha256"],
            )
            self.assertEqual(
                first["immutable_anchor_chain_sha256"],
                second["immutable_anchor_chain_sha256"],
            )

    @patch("tools.final_immutable_manifest_v76_14.git_state")
    def test_output_verifier_pass(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_hash = make_source(root)
            cfg = config()
            cfg["expected_v76_13_verification_sha256"] = source_hash
            cfg["immutable_anchor_chain"]["v76_13"]["verification_sha256"] = source_hash
            mocked_git.return_value = {
                "head_sha": COMMIT,
                "origin_main_sha": COMMIT,
                "branch": "main",
                "tracked_status_short": [],
                "full_status_short": [],
            }
            result = build_final_immutable_manifest(root, cfg)
            out = root / "release/v76_14/output"
            write_outputs(result, out)
            checked = verify_output(out)
            self.assertTrue(checked["verified"])

    @patch("tools.final_immutable_manifest_v76_14.git_state")
    def test_output_verifier_tamper(self, mocked_git):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_hash = make_source(root)
            cfg = config()
            cfg["expected_v76_13_verification_sha256"] = source_hash
            cfg["immutable_anchor_chain"]["v76_13"]["verification_sha256"] = source_hash
            mocked_git.return_value = {
                "head_sha": COMMIT,
                "origin_main_sha": COMMIT,
                "branch": "main",
                "tracked_status_short": [],
                "full_status_short": [],
            }
            result = build_final_immutable_manifest(root, cfg)
            out = root / "release/v76_14/output"
            write_outputs(result, out)
            path = out / "final_immutable_manifest_v76_14.json"
            value = json.loads(path.read_text(encoding="utf-8"))
            value["orders_submitted"] = 1
            path.write_text(json.dumps(value), encoding="utf-8")
            checked = verify_output(out)
            self.assertFalse(checked["verified"])


if __name__ == "__main__":
    unittest.main()
