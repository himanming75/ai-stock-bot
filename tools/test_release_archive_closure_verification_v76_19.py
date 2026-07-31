from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from tools.release_archive_closure_verification_v76_19 import create_closure_verification, digest, validate_config, write_outputs
from tools.verify_release_archive_closure_verification_v76_19 import verify_output

CERT = "b177df9cef0d8107cdcb4ef2a21019c367d0b1878edbb8695a10d2714568b599"
CHAIN = "c12874857d9abdb9a68a0bbcf0104be72f3a8876fafe63490e52c9f41b29dbca"
HEAD = "ad123c7127ecc4bcf80e62bb2d0b6a2e0b761339"

def config():
    return {"verification_scope":"RELEASE_ARCHIVE_CLOSURE_VERIFICATION","offline_only":True,
    "independent_verification_required":True,"require_git_tracked_clean":True,"require_head_matches_origin_main":True,
    "require_framework_commit_match":True,"require_certificate_self_hash":True,"require_closure_chain_self_hash":True,
    "require_fixed_anchor_match":True,"require_zero_failed_gates":True,"require_zero_trading_side_effects":True,
    "network_allowed":False,"broker_connection_allowed":False,"order_submission_allowed":False,
    "live_trading_allowed":False,"live_approval_allowed":False,"expected_framework_commit_sha":HEAD,
    "expected_closure_certificate_sha256":CERT,"expected_closure_chain_sha256":CHAIN}

def source():
    chain = {"framework_commit_sha":"99cc52ce6b3c3676fc086882a585bbca616f1b7b","v76_16_seal_certificate_sha256":"a"*64,
             "v76_16_archive_sha256":"b"*64,"v76_16_archive_manifest_sha256":"c"*64,"v76_16_evidence_set_sha256":"d"*64,
             "v76_17_verification_sha256":"e"*64}
    obj = {"schema_version":"v76.18.release_archive_closure_certificate.1","version":"76.18","certificate_type":"RELEASE_ARCHIVE_CLOSURE_CERTIFICATE",
           "issued_at_utc":"x","duration_seconds":0.1,"status":"PASS","decision":"release_archive_closure_certified",
           "repository":{"framework_commit_sha":"99cc52ce6b3c3676fc086882a585bbca616f1b7b"},"closure_chain":chain,
           "closure_chain_sha256":CHAIN,"certificate_result":{"failed_gate_count":0,"failed_gate_ids":[]},
           "release_archive_closure_certified":True,"release_archive_independently_verified":True,"release_archive_sealed":True,
           "release_candidate_closed":True,"network_allowed":False,"broker_connected":False,"orders_submitted":0,
           "approved_for_live":False,"live_trading_authorized":False,"next_phase":"V76_19_RELEASE_ARCHIVE_CLOSURE_VERIFICATION"}
    obj["closure_certificate_sha256"] = CERT
    return obj

class Tests(unittest.TestCase):
    def test_config(self): validate_config(config())
    def test_digest_deterministic(self): self.assertEqual(digest({"b":2,"a":1}), digest({"a":1,"b":2}))
    def test_pass_and_output_verifier(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); p=root/"release/v76_18/output"; p.mkdir(parents=True)
            s=source()
            # Patch digest only for the two immutable V76.18 anchor calculations; all generated V76.19 hashes remain real.
            real_digest=digest
            def controlled(value):
                if value == s["closure_chain"]: return CHAIN
                immutable={k:v for k,v in s.items() if k not in {"closure_certificate_sha256","issued_at_utc","duration_seconds"}}
                if value == immutable: return CERT
                return real_digest(value)
            (p/"release_archive_closure_certificate_v76_18.json").write_text(json.dumps(s),encoding="utf-8")
            state={"head_sha":HEAD,"origin_main_sha":HEAD,"branch":"main","tracked_status_short":[]}
            with patch("tools.release_archive_closure_verification_v76_19.git_state",return_value=state), patch("tools.release_archive_closure_verification_v76_19.digest",side_effect=controlled):
                result=create_closure_verification(root,config())
            self.assertEqual(result["status"],"PASS")
            out=root/"out"; write_outputs(result,out)
            self.assertTrue(verify_output(out)["verified"])
    def test_anchor_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); p=root/"release/v76_18/output"; p.mkdir(parents=True)
            s=source(); s["closure_certificate_sha256"]="0"*64
            (p/"release_archive_closure_certificate_v76_18.json").write_text(json.dumps(s),encoding="utf-8")
            state={"head_sha":HEAD,"origin_main_sha":HEAD,"branch":"main","tracked_status_short":[]}
            with patch("tools.release_archive_closure_verification_v76_19.git_state",return_value=state):
                result=create_closure_verification(root,config())
            self.assertEqual(result["status"],"FAIL")
            self.assertIn("V76_18_CERTIFICATE_FIXED_ANCHOR",result["verification_result"]["failed_gate_ids"])
if __name__ == "__main__": unittest.main()
