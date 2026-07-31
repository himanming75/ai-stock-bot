from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.release_archive_finalization_v76_20 import (
    create_finalization, digest, load_json, validate_config, write_outputs
)
from tools.verify_release_archive_finalization_v76_20 import verify_output


class V7620Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "broker_connection_allowed": False,
            "expected_framework_commit_sha": "d" * 40,
            "expected_v76_18_closure_certificate_sha256": "a" * 64,
            "expected_v76_18_closure_chain_sha256": "b" * 64,
            "finalization_scope": "RELEASE_ARCHIVE_FINALIZATION",
            "live_approval_allowed": False,
            "live_trading_allowed": False,
            "network_allowed": False,
            "offline_only": True,
            "order_submission_allowed": False,
            "require_finalization_chain": True,
            "require_git_tracked_clean": True,
            "require_head_matches_origin_main": True,
            "require_v76_19_self_hash": True,
            "require_v76_19_verification_chain_self_hash": True,
            "require_v76_19_zero_failed_gates": True,
            "require_zero_trading_side_effects": True,
        }

    def source(self) -> dict:
        source = {
            "schema_version": "v76.19.release_archive_closure_verification.1",
            "status": "PASS",
            "decision": "release_archive_closure_independently_verified",
            "repository": {"framework_commit_sha": "c" * 40},
            "verified_anchors": {
                "v76_18_closure_certificate_sha256": "a" * 64,
                "v76_18_closure_chain_sha256": "b" * 64,
            },
            "verification_chain": {"sample": "chain"},
            "verification_result": {
                "failed_gate_count": 0, "failed_gate_ids": []
            },
            "release_archive_closure_independently_verified": True,
            "release_archive_closure_certified": True,
            "release_archive_sealed": True,
            "release_candidate_closed": True,
            "network_allowed": False,
            "broker_connected": False,
            "orders_submitted": 0,
            "approved_for_live": False,
            "live_trading_authorized": False,
            "next_phase": "V76_20_RELEASE_ARCHIVE_FINALIZATION",
        }
        source["verification_chain_sha256"] = digest(source["verification_chain"])
        source["verification_sha256"] = digest(source)
        return source

    def test_config(self) -> None:
        validate_config(self.config)

    def test_digest_deterministic(self) -> None:
        self.assertEqual(digest({"b": 2, "a": 1}), digest({"a": 1, "b": 2}))

    def test_pass_and_output_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_dir = root / "release/v76_19/output"
            source_dir.mkdir(parents=True)
            (source_dir / "release_archive_closure_verification_v76_19.json").write_text(
                json.dumps(self.source()), encoding="utf-8"
            )
            git = {
                "head_sha": "d" * 40, "origin_main_sha": "d" * 40,
                "branch": "main", "tracked_status_short": [],
            }
            with patch("tools.release_archive_finalization_v76_20.git_state",
                       return_value=git):
                result = create_finalization(root, self.config)
            self.assertEqual(result["status"], "PASS")
            output = root / "release/v76_20/output"
            write_outputs(result, output)
            self.assertTrue(verify_output(output)["verified"])

    def test_tampered_source_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.source()
            source["orders_submitted"] = 1
            source_dir = root / "release/v76_19/output"
            source_dir.mkdir(parents=True)
            (source_dir / "release_archive_closure_verification_v76_19.json").write_text(
                json.dumps(source), encoding="utf-8"
            )
            git = {
                "head_sha": "d" * 40, "origin_main_sha": "d" * 40,
                "branch": "main", "tracked_status_short": [],
            }
            with patch("tools.release_archive_finalization_v76_20.git_state",
                       return_value=git):
                result = create_finalization(root, self.config)
            self.assertEqual(result["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
