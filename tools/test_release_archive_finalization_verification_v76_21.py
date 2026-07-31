from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.release_archive_finalization_verification_v76_21 import (
    create_verification,
    digest,
    validate_config,
    write_outputs,
)
from tools.verify_release_archive_finalization_verification_v76_21 import (
    verify_output,
)


class V7621Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = {
            "broker_connection_allowed": False,
            "expected_finalization_chain_sha256": "b" * 64,
            "expected_finalization_sha256": "a" * 64,
            "expected_framework_commit_sha": "d" * 40,
            "independent_verification_required": True,
            "live_approval_allowed": False,
            "live_trading_allowed": False,
            "network_allowed": False,
            "offline_only": True,
            "order_submission_allowed": False,
            "require_finalization_chain_self_hash": True,
            "require_finalization_self_hash": True,
            "require_fixed_anchor_match": True,
            "require_git_tracked_clean": True,
            "require_head_matches_origin_main": True,
            "require_v76_20_zero_failed_gates": True,
            "require_zero_trading_side_effects": True,
            "verification_scope":
                "RELEASE_ARCHIVE_FINALIZATION_VERIFICATION",
        }

    def source(self) -> dict:
        source = {
            "schema_version":
                "v76.20.release_archive_finalization.1",
            "record_type": "RELEASE_ARCHIVE_FINALIZATION",
            "status": "PASS",
            "decision": "release_archive_finalized",
            "repository": {"framework_commit_sha": "c" * 40},
            "finalization_chain": {"sample": "chain"},
            "finalization_result": {
                "failed_gate_count": 0,
                "failed_gate_ids": [],
            },
            "release_archive_finalized": True,
            "release_archive_closure_independently_verified": True,
            "release_archive_closure_certified": True,
            "release_archive_sealed": True,
            "release_candidate_closed": True,
            "network_allowed": False,
            "broker_connected": False,
            "orders_submitted": 0,
            "approved_for_live": False,
            "live_trading_authorized": False,
            "next_phase":
                "V76_21_RELEASE_ARCHIVE_FINALIZATION_VERIFICATION",
        }
        source["finalization_chain_sha256"] = digest(
            source["finalization_chain"]
        )
        source["finalization_sha256"] = digest(source)
        return source

    def test_config(self) -> None:
        validate_config(self.config)

    def test_digest_deterministic(self) -> None:
        self.assertEqual(
            digest({"b": 2, "a": 1}),
            digest({"a": 1, "b": 2}),
        )

    def test_pass_and_output_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.source()
            self.config["expected_finalization_sha256"] = (
                source["finalization_sha256"]
            )
            self.config["expected_finalization_chain_sha256"] = (
                source["finalization_chain_sha256"]
            )
            source_dir = root / "release/v76_20/output"
            source_dir.mkdir(parents=True)
            (
                source_dir /
                "release_archive_finalization_v76_20.json"
            ).write_text(json.dumps(source), encoding="utf-8")

            git = {
                "head_sha": "d" * 40,
                "origin_main_sha": "d" * 40,
                "branch": "main",
                "tracked_status_short": [],
            }
            with patch(
                "tools.release_archive_finalization_verification_v76_21.git_state",
                return_value=git,
            ):
                result = create_verification(root, self.config)

            self.assertEqual(result["status"], "PASS")
            output = root / "release/v76_21/output"
            write_outputs(result, output)
            self.assertTrue(verify_output(output)["verified"])

    def test_tampered_source_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.source()
            self.config["expected_finalization_sha256"] = (
                source["finalization_sha256"]
            )
            self.config["expected_finalization_chain_sha256"] = (
                source["finalization_chain_sha256"]
            )
            source["orders_submitted"] = 1
            source_dir = root / "release/v76_20/output"
            source_dir.mkdir(parents=True)
            (
                source_dir /
                "release_archive_finalization_v76_20.json"
            ).write_text(json.dumps(source), encoding="utf-8")

            git = {
                "head_sha": "d" * 40,
                "origin_main_sha": "d" * 40,
                "branch": "main",
                "tracked_status_short": [],
            }
            with patch(
                "tools.release_archive_finalization_verification_v76_21.git_state",
                return_value=git,
            ):
                result = create_verification(root, self.config)

            self.assertEqual(result["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
