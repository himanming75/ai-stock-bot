from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

from tools.release_archive_completion_certificate_verification_v76_23 import (
    create_verification, digest, validate_config, write_outputs
)
from tools.verify_release_archive_completion_certificate_verification_v76_23 import verify_output

class V7623Tests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "verification_scope":"RELEASE_ARCHIVE_COMPLETION_CERTIFICATE_VERIFICATION",
            "expected_framework_commit_sha":"d"*7,
            "expected_certificate_sha256":"a"*64,
            "expected_completion_chain_sha256":"b"*64,
            "offline_only":True,
            "independent_verification_required":True,
            "require_git_tracked_clean":True,
            "require_head_matches_origin_main":True,
            "require_certificate_self_hash":True,
            "require_completion_chain_self_hash":True,
            "require_fixed_anchor_match":True,
            "require_v76_22_zero_failed_gates":True,
            "require_zero_trading_side_effects":True,
            "network_allowed":False,
            "broker_connection_allowed":False,
            "order_submission_allowed":False,
            "live_trading_allowed":False,
            "live_approval_allowed":False,
        }

    def source(self):
        s = {
            "schema_version":"v76.22.release_archive_completion_certificate.1",
            "record_type":"RELEASE_ARCHIVE_COMPLETION_CERTIFICATE",
            "status":"PASS",
            "decision":"release_archive_completion_certified",
            "repository":{"framework_commit_sha":"c"*40},
            "completion_chain":{"sample":"chain"},
            "certificate_result":{"failed_gate_count":0,"failed_gate_ids":[]},
            "release_archive_completion_certified":True,
            "release_archive_finalization_independently_verified":True,
            "release_archive_finalized":True,
            "release_archive_closure_independently_verified":True,
            "release_archive_closure_certified":True,
            "release_archive_sealed":True,
            "release_candidate_closed":True,
            "network_allowed":False,
            "broker_connected":False,
            "orders_submitted":0,
            "approved_for_live":False,
            "live_trading_authorized":False,
            "next_phase":"V76_23_RELEASE_ARCHIVE_COMPLETION_CERTIFICATE_VERIFICATION",
        }
        s["completion_chain_sha256"] = digest(s["completion_chain"])
        s["certificate_sha256"] = digest(s)
        return s

    def test_config(self):
        validate_config(self.config)

    def test_digest_deterministic(self):
        self.assertEqual(digest({"b":2,"a":1}), digest({"a":1,"b":2}))

    def test_pass_and_output_verifier(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.source()
            self.config["expected_certificate_sha256"] = source["certificate_sha256"]
            self.config["expected_completion_chain_sha256"] = source["completion_chain_sha256"]
            d = root/"release/v76_22/output"
            d.mkdir(parents=True)
            (d/"release_archive_completion_certificate_v76_22.json").write_text(json.dumps(source), encoding="utf-8")
            git = {"head_sha":"d"*40,"head_short_sha":"d"*7,"origin_main_sha":"d"*40,
                   "branch":"main","tracked_status_short":[]}
            with patch("tools.release_archive_completion_certificate_verification_v76_23.git_state", return_value=git):
                result = create_verification(root, self.config)
            self.assertEqual(result["status"], "PASS")
            out = root/"release/v76_23/output"
            write_outputs(result, out)
            self.assertTrue(verify_output(out)["verified"])

    def test_tampered_source_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.source()
            self.config["expected_certificate_sha256"] = source["certificate_sha256"]
            self.config["expected_completion_chain_sha256"] = source["completion_chain_sha256"]
            source["orders_submitted"] = 1
            d = root/"release/v76_22/output"
            d.mkdir(parents=True)
            (d/"release_archive_completion_certificate_v76_22.json").write_text(json.dumps(source), encoding="utf-8")
            git = {"head_sha":"d"*40,"head_short_sha":"d"*7,"origin_main_sha":"d"*40,
                   "branch":"main","tracked_status_short":[]}
            with patch("tools.release_archive_completion_certificate_verification_v76_23.git_state", return_value=git):
                result = create_verification(root, self.config)
            self.assertEqual(result["status"], "FAIL")

if __name__ == "__main__":
    unittest.main()
