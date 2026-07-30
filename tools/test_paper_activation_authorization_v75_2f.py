import copy
import json
import tempfile
import unittest
from pathlib import Path

from tools.paper_activation_authorization_v75_2f import (
    PaperActivationAuthorizationError,
    build_authorization,
    deterministic_authorization_id,
    main,
    sha256_of,
)


def with_hash(obj, field):
    obj = copy.deepcopy(obj)
    obj[field] = sha256_of(obj)
    return obj


def source_fixture():
    checklist = [
        {"review_index": i, "review_item": f"ITEM_{i}", "operator_confirmed": True, "state": "CONFIRMED"}
        for i in range(1, 6)
    ]
    decision_id = "POD-0123456789ABCDEF"
    source_review_hash = "a" * 64
    operator = {
        "operator_name": "James Park",
        "operator_signature": "James Park / manually signed",
        "reason": "Reviewed all paper-only controls.",
        "signed_at": "2026-07-30T13:24:48-07:00",
        "signature_verified": True,
    }
    evidence = {
        "decision_id": decision_id,
        "review_id": "POR-0123456789ABCDEF",
        "selected_decision": "APPROVE_PAPER",
        "operator_name": operator["operator_name"],
        "operator_signature": operator["operator_signature"],
        "reason": operator["reason"],
        "signed_at": operator["signed_at"],
        "source_review_sha256": source_review_hash,
    }
    operator["signature_evidence_sha256"] = sha256_of(evidence)
    ledger = [
        {"ledger_index": 1, "event": "A", "state": "PASS", "decision_id": decision_id},
        {"ledger_index": 2, "event": "B", "state": "PASS", "decision_id": decision_id},
    ]
    source = {
        "status": "PASS",
        "decision": "paper_operator_decision_recorded",
        "decision_id": decision_id,
        "decision_state": "APPROVED_FOR_PAPER_ACTIVATION_PREPARATION",
        "next_state": "READY_FOR_PAPER_ACTIVATION_AUTHORIZATION",
        "selected_decision": "APPROVE_PAPER",
        "review_id": "POR-0123456789ABCDEF",
        "preflight_id": "PDP-0123456789ABCDEF",
        "bundle_id": "PDB-0123456789ABCDEF",
        "session_id": "PAPER-0123456789ABCDEF",
        "champion_candidate_id": "CAND-A",
        "operator_record": operator,
        "confirmed_checklist": checklist,
        "confirmed_checklist_sha256": sha256_of(checklist),
        "decision_ledger": ledger,
        "decision_ledger_sha256": sha256_of(ledger),
        "source_paper_operator_review_package_sha256": source_review_hash,
        "activation_gate": {
            "paper_activation_preparation_allowed": True,
            "activation_allowed": False,
            "live_activation_allowed": False,
            "operator_decision_recorded": True,
            "operator_signature_verified": True,
            "next_version": "75.2F",
        },
        "safety_lock": {
            "network_enabled": False,
            "live_orders_enabled": False,
            "broker_credentials_required": False,
            "external_side_effects_allowed": False,
            "automatic_approval_allowed": False,
            "lock_state": "ENFORCED",
        },
        "approved_for_live": False,
        "network_used": False,
        "schema_version": "v75.2e.paper_operator_decision_record.1",
        "version": "75.2E",
    }
    return with_hash(source, "paper_operator_decision_record_sha256")


def config_fixture():
    return {
        "require_signed_operator_decision": True,
        "require_confirmed_checklist": True,
        "require_offline_paper_mode": True,
        "single_use_authorization": True,
        "network_enabled": False,
        "live_orders_enabled": False,
        "broker_credentials_required": False,
        "automatic_activation_allowed": False,
        "live_trading_approval_allowed": False,
        "authorization_ttl_seconds": 3600,
    }


class TestV752F(unittest.TestCase):
    def build(self):
        return build_authorization(source_fixture(), config_fixture(), "2026-07-30T20:40:00+00:00")

    def test_pass(self): self.assertEqual(self.build()["status"], "PASS")
    def test_version_schema(self):
        x = self.build()
        self.assertEqual(x["version"], "75.2F")
        self.assertEqual(x["schema_version"], "v75.2f.paper_activation_authorization.1")
    def test_state(self): self.assertEqual(self.build()["authorization_state"], "AUTHORIZED_NOT_ACTIVATED")
    def test_scope(self): self.assertEqual(self.build()["authorization_scope"], "OFFLINE_PAPER_ACTIVATION_ONLY")
    def test_authorized(self): self.assertTrue(self.build()["activation_gate"]["paper_activation_authorized"])
    def test_not_activated(self): self.assertFalse(self.build()["activation_gate"]["activation_executed"])
    def test_activation_still_blocked(self): self.assertFalse(self.build()["activation_gate"]["activation_allowed"])
    def test_live_false(self): self.assertFalse(self.build()["approved_for_live"])
    def test_network_false(self): self.assertFalse(self.build()["network_used"])
    def test_token_single_use(self):
        t = self.build()["activation_token"]
        self.assertTrue(t["single_use"])
        self.assertFalse(t["consumed"])
    def test_token_length(self): self.assertEqual(len(self.build()["activation_token"]["token_sha256"]), 64)
    def test_checks(self): self.assertEqual(len(self.build()["authorization_checks"]), 7)
    def test_ledger(self): self.assertEqual(len(self.build()["authorization_ledger"]), 5)
    def test_hash(self):
        x = self.build()
        h = x.pop("paper_activation_authorization_sha256")
        self.assertEqual(h, sha256_of(x))
    def test_deterministic_id(self):
        self.assertEqual(
            deterministic_authorization_id("D", "H", "T"),
            deterministic_authorization_id("D", "H", "T"),
        )
    def test_reject_source(self):
        s = source_fixture()
        s.pop("paper_operator_decision_record_sha256")
        s["selected_decision"] = "REJECT"
        s = with_hash(s, "paper_operator_decision_record_sha256")
        self.assertRaises(PaperActivationAuthorizationError, build_authorization, s, config_fixture())
    def test_bad_integrity(self):
        s = source_fixture()
        s["decision_id"] = "BAD"
        self.assertRaises(PaperActivationAuthorizationError, build_authorization, s, config_fixture())
    def test_bad_signature_evidence(self):
        s = source_fixture()
        s.pop("paper_operator_decision_record_sha256")
        s["operator_record"]["signature_evidence_sha256"] = "0" * 64
        s = with_hash(s, "paper_operator_decision_record_sha256")
        self.assertRaises(PaperActivationAuthorizationError, build_authorization, s, config_fixture())
    def test_unconfirmed_checklist(self):
        s = source_fixture()
        s.pop("paper_operator_decision_record_sha256")
        s["confirmed_checklist"][0]["operator_confirmed"] = False
        s["confirmed_checklist_sha256"] = sha256_of(s["confirmed_checklist"])
        s = with_hash(s, "paper_operator_decision_record_sha256")
        self.assertRaises(PaperActivationAuthorizationError, build_authorization, s, config_fixture())
    def test_bad_config(self):
        c = config_fixture()
        c["automatic_activation_allowed"] = True
        self.assertRaises(PaperActivationAuthorizationError, build_authorization, source_fixture(), c)
    def test_bad_ttl(self):
        c = config_fixture()
        c["authorization_ttl_seconds"] = 10
        self.assertRaises(PaperActivationAuthorizationError, build_authorization, source_fixture(), c)
    def test_main_success_failure(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p / "s.json").write_text(json.dumps(source_fixture()), encoding="utf-8")
            (p / "c.json").write_text(json.dumps(config_fixture()), encoding="utf-8")
            self.assertEqual(main(["--input", str(p/"s.json"), "--config", str(p/"c.json"), "--output-dir", str(p/"out")]), 0)
            self.assertTrue((p/"out"/"paper_activation_authorization_v75_2f.json").is_file())
            self.assertEqual(main(["--input", str(p/"missing.json"), "--config", str(p/"c.json"), "--output-dir", str(p/"bad")]), 1)


if __name__ == "__main__":
    unittest.main()
